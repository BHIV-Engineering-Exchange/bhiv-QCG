# INITIAL REQUIREMENTS REGISTER & HARDWARE DEPENDENCY MAP
## BHQ Sovereign Quantum Computing, Photonic Systems & BioQuantum Research
### Task ID: BHQ-INFRA-001 (Phase 4 Checkpoint)

**Programme Lead:** Ganesh Vishwakarma  
**Platform Integration Lead:** Kanishk Singh  
**Trust & Instrumentation Lead:** Pritesh Patra  
**Runtime & Biological Simulation Lead:** Dhiraj & Candidate on Test Task  
**Document Identifier:** `BHQ-INFRA-001-REQ-001`  
**Date:** 2026-11-14  

---

## 1. Computational Requirements Register

| Req ID | Domain / Workstream | Parameter / Metric | Required Specification | Tolerable Range | Verification Method | Current Status |
|:---|:---:|:---|:---|:---:|:---:|:---:|
| **`REQ-CMP-01`** | WS-A (Quantum Algorithms) | Circuit Simulation Qubit Capacity | $\ge 24$ state-vector qubits | $16\text{--}32$ qubits | Qiskit `AerSimulator` benchmark | `SIMULATED AND TESTED` |
| **`REQ-CMP-02`** | WS-A (Quantum Algorithms) | QAOA Gate Compilation Latency | $\le 250.0\,\text{ms}$ for $N=6$ | $\le 500.0\,\text{ms}$ | Qiskit compiler test | `SIMULATED AND TESTED` |
| **`REQ-CMP-03`** | WS-B (Biological Networks) | Spatial Grid Node Capacity | $\ge 12$ spatial food sites | $10\text{--}50$ nodes | `SIMULATION/mycelium_network_model.py` | `SIMULATED AND TESTED` |
| **`REQ-CMP-04`** | WS-B (Biological Networks) | Dynamic Transport Iteration Step | $dt = 0.1\,\text{s}$ over 120 steps | $dt \in [0.05, 0.2]\,\text{s}$ | Convergence to steady-state flux | `SIMULATED AND TESTED` |
| **`REQ-CMP-05`** | WS-D (Cryptographic Provenance)| ECDSA P-256 Signing Throughput | $\ge 100\,\text{records/s}$ | $\ge 50\,\text{records/s}$ | `test_qcg_provenance.py` (100 in 0.08s) | `IMPLEMENTED AND TESTED`|
| **`REQ-CMP-06`** | WS-D (Cryptographic Provenance)| Merkle Inclusion Proof Validation | $\le 1.0\,\text{ms}$ per leaf | $\le 5.0\,\text{ms}$ | Pairwise SHA-256 tree audit | `IMPLEMENTED AND TESTED`|

---

## 2. Physical & Cryogenic Requirements Register (WS-D)

| Req ID | Cryogenic Stage | Temperature Setpoint | Maximum Permissible Heat Load | Sensor / Gauge Requirement | Current Status |
|:---|:---|:---:|:---:|:---|:---:|
| **`REQ-CRY-01`** | Room Temperature Plate | $295.0\text{--}300.0\,\text{K}$ | Ambient convection | PT100 platinum RTD | `PROPOSED BUT UNIMPLEMENTED` |
| **`REQ-CRY-02`** | 50 K Flange Stage | $45.0\text{--}55.0\,\text{K}$ | $\le 30.0\,\text{W}$ | Silicon Diode (DT-670) | `PROPOSED BUT UNIMPLEMENTED` |
| **`REQ-CRY-03`** | 4 K Plate Stage | $3.8\text{--}4.2\,\text{K}$ | $\le 1.5\,\text{W}$ | Cernox CX-1050 calibrated | `PROPOSED BUT UNIMPLEMENTED` |
| **`REQ-CRY-04`** | Still Plate Stage | $0.75\text{--}0.90\,\text{K}$ | $\le 20.0\,\text{mW}$ | Ruthenium Oxide ($\text{RuO}_2$) | `PROPOSED BUT UNIMPLEMENTED` |
| **`REQ-CRY-05`** | Cold Plate Stage | $90.0\text{--}110.0\,\text{mK}$ | $\le 100.0\,\mu\text{W}$ | Ruthenium Oxide ($\text{RuO}_2$) | `PROPOSED BUT UNIMPLEMENTED` |
| **`REQ-CRY-06`** | Mixing Chamber (MXC) | $\le 15.0\,\text{mK}$ (Base $\approx 10\,\text{mK}$) | $\le 15.0\,\mu\text{W}$ at $20\,\text{mK}$ | Calibrated $\text{RuO}_2$ + CMN thermometer | `PROPOSED BUT UNIMPLEMENTED` |
| **`REQ-CRY-07`** | Cryostat Vacuum Jacket | $\le 1.0 \times 10^{-6}\,\text{mbar}$ | OVC high vacuum isolation | Cold cathode / Penning gauge | `PROPOSED BUT UNIMPLEMENTED` |
| **`REQ-CRY-08`** | Magnetic Shielding | $\le 1.0\,\mu\text{T}$ residual flux | Cryogenic Mu-metal / Cryoperm | Fluxgate magnetometer sweep | `PROPOSED BUT UNIMPLEMENTED` |

---

## 3. Microwave, Photonic & Instrumentation Requirements (WS-C & WS-D)

| Req ID | Subsystem | Parameter | Required Specification | Tolerable Range | Modeled Value | Status |
|:---|:---|:---|:---:|:---:|:---:|:---:|
| **`REQ-INS-01`** | Readout Signal Chain | Total System Gain | $80.0\,\text{dB}$ | $78.0\text{--}82.0\,\text{dB}$ | $80.00\,\text{dB}$ | `SIMULATED AND TESTED` |
| **`REQ-INS-02`** | Readout Signal Chain | System Noise Temp ($T_{\text{sys}}$) | $\le 4.0\,\text{K}$ | $0.1\text{--}4.0\,\text{K}$ | $0.1402\,\text{K}$ | `SIMULATED AND TESTED` |
| **`REQ-INS-03`** | Timing Synchronization| Inter-Channel Skew ($\Delta t_{\text{skew}}$)| $\le 10.0\,\text{ps}$ | $\le 20.0\,\text{ps}$ | $6.20\,\text{ps}$ | `SIMULATED AND TESTED` |
| **`REQ-INS-04`** | Timing Synchronization| Total Clock Jitter ($\sigma_{\text{jitter}}$)| $\le 100.0\,\text{ps}$ | $\le 100.0\,\text{ps}$ | $4.416\,\text{ps}$ | `SIMULATED AND TESTED` |
| **`REQ-INS-05`** | Microwave Attenuation | Total Control Line Attenuation | $\ge 50.0\,\text{dB}$ | $50\text{--}60\,\text{dB}$ | $50.0\,\text{dB}$ | `SIMULATED AND TESTED` |
| **`REQ-INS-06`** | Thermal Noise Occupancy| MXC Thermal Occupation ($n_{\text{th}}$) | $\le 1.0 \times 10^{-3}$ | $\le 1.0 \times 10^{-3}$ | $3.79 \times 10^{-11}$ | `SIMULATED AND TESTED` |
| **`REQ-INS-07`** | Optical Fiber Link | Single-Mode Attenuation ($\alpha$) | $\le 0.20\,\text{dB/km}$ | $0.18\text{--}0.22\,\text{dB/km}$ | $0.20\,\text{dB/km}$ | `SIMULATED AND TESTED` |
| **`REQ-INS-08`** | Quantum Communication | QBER at $L=50\,\text{km}$ | $\le 11.0\%$ threshold | $\le 11.0\%$ | $0.000006\%$ | `SIMULATED AND TESTED` |

---

## 4. Energy & Sustainability Requirements (Rules 4 & 5)

| Req ID | Focus Area | Parameter | Engineering Requirement | Scientific Boundary / Rule |
|:---|:---|:---|:---|:---|
| **`REQ-ENG-01`** | Ambient RF Harvesting | Minimum Power Density | $P_{\text{density}} \ge -20.0\,\text{dBm}$ ($\approx 10\,\mu\text{W/cm}^2$) | **Rule 4:** Ambient RF energy must be measured in situ before claiming energy self-sufficiency. Below $-20\,\text{dBm}$, diode rectenna conversion efficiency is $< 3\%$. |
| **`REQ-ENG-02`** | Cryogenic Cooling Power | Wall-Plug Energy Budget | $\le 15.0\,\text{kW}$ electrical load per cryostat | **Rule 5:** Evaluated against classical server farm executing equivalent 24-qubit matrix inversion ($< 2.5\,\text{kW}$). |
| **`REQ-ENG-03`** | Biological Growth Energy | Nutrient Solution Caloric Density | $\approx 20.0\,\text{g/L}$ malt extract agar ($< 1\,\text{W}$ equivalent) | **Rule 5:** Low energy footprint, but transport latency is $10^8 \times$ slower than optical or electronic circuits. |

---

## 5. Hardware Dependency Map & Unknown Parameters

```
[Level 0: Verified Simulation]
  ├── AerSimulator Qiskit Runtime (WS-A)
  ├── Mycelium Adaptive Flux Network (WS-B)
  ├── Remediated Superdense Coding & Link Budget (WS-C)
  └── Friis Cascade & Timing Skew Models (WS-D)
          |
          v (Requires Physical Characterization)
[Level 1: Unresolved Parameters & Environmental Measurements]
  ├── UNK-01: In-situ ambient RF power density spectrum (100 MHz - 6 GHz)
  ├── UNK-02: True biological action-potential conduction velocity in Pleurotus ostreatus (0.5 - 5 mm/s)
  ├── UNK-03: Dilution refrigerator optical fiber feedthrough insertion loss & thermal dissipation
  └── UNK-04: Transmon qubit T1/T2 relaxation times under proposed 50 dB attenuation cascade
          |
          v (Requires Technical Feasibility & Board Approval)
[Level 2: Specialised Equipment Selection - PREREQUISITE GATED]
  ├── TWPA (Traveling Wave Parametric Amplifier) (Cryogenic 10 mK)
  ├── High Electron Mobility Transistor (HEMT) (Cryogenic 4 K)
  ├── White Rabbit Timing Grandmaster & Synchronous Ethernet Switch
  ├── Arbitrary Waveform Generator (AWG) & Digitizer Chassis (>= 1 GSa/s, 14-bit)
  └── Optical Single-Photon Detector (SNSPD) Cryogenic Unit
          |
          v (Hardware Procurement: STRICTLY NOT AUTHORISED)
[Level 3: Physical Procurement & Fabrication]
  └── BLOCKED until Level 1 & 2 prerequisites are 100% satisfied.
```
