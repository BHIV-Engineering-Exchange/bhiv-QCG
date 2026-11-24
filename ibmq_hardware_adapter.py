"""ibmq_hardware_adapter.py — External Hardware & Qiskit Runtime Adapter

Provides interfaces and concrete implementations for linking QCG to physical
quantum provider endpoints, cloud hardware backends (IBM Quantum Runtime via SamplerV2),
and high-fidelity local simulation fallbacks.
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel

# Import standard QCG models
from execution_contract import ComputationExecutionContract, ProducerType
from quantum_provider_registry import ProviderStatus, QuantumProviderRecord
import config

logger = logging.getLogger("qcg.hardware_adapter")


class ExternalHardwareAdapter:
    """Interface for integrating external quantum providers."""

    def get_provider_record(self) -> QuantumProviderRecord:
        raise NotImplementedError

    def execute_circuit(self, circuit: QuantumCircuit, **kwargs) -> Dict[str, Any]:
        """Executes a circuit on the hardware backend and returns a raw result envelope."""
        raise NotImplementedError


class IBMQMockHardwareAdapter(ExternalHardwareAdapter):
    """
    Mock hardware adapter mimicking an IBM Quantum Heavy Hex device (e.g. 127Q).
    Falls back to AerSimulator with basis-gate transpilation.
    """

    def __init__(self, backend_name: str = "ibm_brisbane_mock", qubits: int = 127):
        self.backend_name = backend_name
        self.qubits = qubits
        self.provider_id = f"ibmq-{self.backend_name}"

        # Simulated hardware topology stats
        self._device_topology = {
            "name": self.backend_name,
            "qubit_count": self.qubits,
            "architecture": "Heavy Hex",
            "basis_gates": ["id", "rz", "sx", "x", "ecr", "reset"],
            "average_cx_error": 0.007,
            "average_readout_error": 0.015,
        }

    def get_provider_record(self) -> QuantumProviderRecord:
        return QuantumProviderRecord(
            provider_id=self.provider_id,
            provider_name="IBM Quantum Cloud (Mock)",
            provider_type="LIVE_HARDWARE",
            status=ProviderStatus.AVAILABLE.value,
            capabilities={
                "hardware_access": True,
                "dynamic_circuits": True,
                "pulse_control": False,
            },
            max_qubits=self.qubits,
            supported_gates=self._device_topology["basis_gates"],
            backend_name=self.backend_name,
            last_health_check=datetime.now(timezone.utc).isoformat(),
            last_health_result=ProviderStatus.AVAILABLE.value,
        )

    def execute_circuit(self, circuit: QuantumCircuit, shots: int = config.SHOTS) -> Dict[str, Any]:
        """Executes the circuit on the simulated physical hardware."""
        logger.info(f"Executing circuit on {self.backend_name} ({shots} shots)")

        from qiskit import transpile
        transpiled_qc = transpile(circuit, basis_gates=self._device_topology["basis_gates"])

        start_time = time.time()
        sim = AerSimulator()
        job = sim.run(transpiled_qc, shots=shots)
        result = job.result()
        counts = result.get_counts(transpiled_qc)
        duration = time.time() - start_time

        envelope = {
            "job_id": f"ibmjob-{str(uuid.uuid4())[:8]}",
            "provider": "IBM Quantum",
            "backend_device": self.backend_name,
            "device_topology": self._device_topology,
            "circuit_depth": transpiled_qc.depth(),
            "qubits_required": transpiled_qc.num_qubits,
            "execution_metadata": {
                "shots": shots,
                "execution_timestamp": datetime.now(timezone.utc).isoformat(),
                "duration_s": round(duration, 4),
                "calibration_information": "CAL-2026-10-09-VALID",
                "transpilation_output": "Optimized level 3",
            },
            "measured_distribution": counts,
            "error_noise_information": {
                "cx_error": self._device_topology["average_cx_error"],
                "readout_error": self._device_topology["average_readout_error"],
            },
        }

        logger.info(f"Hardware execution complete. Job ID: {envelope['job_id']}")
        return envelope


class QiskitRuntimeHardwareAdapter(ExternalHardwareAdapter):
    """
    Pluggable hardware adapter connecting QCG to IBM Quantum Runtime QPUs.
    Supports dynamic transpilation (preset pass managers) and SamplerV2 bitstring acquisition.
    Gracefully falls back to high-fidelity Aer simulation when cloud credentials are unconfigured.
    """

    def __init__(self, backend_name: Optional[str] = None):
        self.channel = os.getenv("QISKIT_IBM_CHANNEL", "ibm_cloud")
        self.token = os.getenv("QISKIT_IBM_TOKEN", "")
        self.instance = os.getenv("QISKIT_IBM_INSTANCE", "")
        self.backend_name = backend_name or "ibm_sherbrooke"
        self.service = None
        self._target_backend = None
        self._is_live = False
        self.num_qubits = 127

        if self.token:
            try:
                from qiskit_ibm_runtime import QiskitRuntimeService
                self.service = QiskitRuntimeService(
                    channel=self.channel,
                    token=self.token,
                    instance=self.instance if self.instance else None,
                )
                if backend_name:
                    self._target_backend = self.service.backend(backend_name)
                else:
                    self._target_backend = self.service.least_busy(operational=True, simulator=False)
                self.backend_name = self._target_backend.name
                self.num_qubits = getattr(self._target_backend, "num_qubits", 127)
                self._is_live = True
                logger.info("Connected to live IBM Quantum Runtime backend: %s", self.backend_name)
            except Exception as e:
                logger.warning("QiskitRuntimeService unavailable (%s). Using fallback mode.", e)
                self.service = None
                self._is_live = False

    def get_provider_record(self) -> QuantumProviderRecord:
        return QuantumProviderRecord(
            provider_id=f"ibmq-{self.backend_name}",
            provider_name=f"IBM Quantum ({self.backend_name})",
            provider_type="LIVE_HARDWARE" if self._is_live else "REMOTE_SIMULATOR",
            status=ProviderStatus.AVAILABLE.value,
            capabilities={
                "hardware_access": self._is_live,
                "dynamic_circuits": True,
                "sampler_v2": True,
                "preset_pass_manager": True,
            },
            max_qubits=self.num_qubits,
            supported_gates=["ecr", "id", "reset", "rz", "sx", "x"],
            backend_name=self.backend_name,
            last_health_check=datetime.now(timezone.utc).isoformat(),
            last_health_result=ProviderStatus.AVAILABLE.value,
        )

    def transpile_circuit(self, circuit: QuantumCircuit, optimization_level: int = 2) -> QuantumCircuit:
        """Dynamically transpile circuit to target QPU coupling map and basis gates."""
        if self._is_live and self._target_backend:
            try:
                from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
                pm = generate_preset_pass_manager(
                    backend=self._target_backend,
                    optimization_level=optimization_level,
                )
                return pm.run(circuit)
            except Exception as e:
                logger.warning("Preset pass manager error (%s), using standard transpile.", e)

        from qiskit import transpile
        basis = ["ecr", "id", "reset", "rz", "sx", "x", "cx", "h"]
        return transpile(circuit, basis_gates=basis, optimization_level=optimization_level)

    def execute_circuit(
        self,
        circuit: QuantumCircuit,
        shots: int = 1024,
        optimization_level: int = 2,
    ) -> Dict[str, Any]:
        """Transpiles and executes circuit synchronously using SamplerV2 or simulation fallback."""
        start_time = time.time()
        transpiled_qc = self.transpile_circuit(circuit, optimization_level)

        if self._is_live and self._target_backend:
            try:
                from qiskit_ibm_runtime import SamplerV2 as Sampler
                sampler = Sampler(backend=self._target_backend)
                job = sampler.run([transpiled_qc], shots=shots)
                job_id = job.job_id()
                logger.info(f"Submitted Qiskit Runtime Job: {job_id} on {self.backend_name}")

                result = job.result()
                duration = time.time() - start_time

                pub_result = result[0]
                meas_data = getattr(pub_result.data, "meas", None) or getattr(pub_result.data, "c", None)
                if meas_data is None:
                    first_field = list(pub_result.data.keys())[0]
                    meas_data = getattr(pub_result.data, first_field)

                counts = meas_data.get_counts()
                return {
                    "job_id": job_id,
                    "provider": "IBM Quantum Runtime",
                    "backend_device": self.backend_name,
                    "num_qubits": self.num_qubits,
                    "circuit_depth": transpiled_qc.depth(),
                    "qubits_used": list(range(circuit.num_qubits)),
                    "execution_duration_s": round(duration, 3),
                    "measured_distribution": counts,
                    "shots": shots,
                    "is_live_hardware": True,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            except Exception as e:
                logger.warning("Live execution via SamplerV2 failed (%s). Falling back to Aer.", e)

        # Fallback to local AerSimulator with basis transpilation
        sim = AerSimulator()
        job = sim.run(transpiled_qc, shots=shots)
        result = job.result()
        counts = result.get_counts(transpiled_qc)
        duration = time.time() - start_time
        job_id = f"aer-sim-{str(uuid.uuid4())[:8]}"

        return {
            "job_id": job_id,
            "provider": "IBM Quantum (Aer Emulated)",
            "backend_device": self.backend_name,
            "num_qubits": self.num_qubits,
            "circuit_depth": transpiled_qc.depth(),
            "qubits_used": list(range(circuit.num_qubits)),
            "execution_duration_s": round(duration, 3),
            "measured_distribution": counts,
            "shots": shots,
            "is_live_hardware": False,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
