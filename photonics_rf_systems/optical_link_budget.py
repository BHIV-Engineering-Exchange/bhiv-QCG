"""
photonics_rf_systems.optical_link_budget
========================================
Optical Fiber Quantum Communication Link Budget & QBER Simulation.
Remediates BLK-PHO-001 (P1).

Physics & Mathematical Formulation:
-----------------------------------
1. Single-Mode Fiber (SMF-28) Transmission:
   Operating in telecom C-band (lambda = 1550 nm):
   - Fiber attenuation coefficient: alpha = 0.2 dB/km
   - Attenuation at distance L: A_dB(L) = alpha * L
   - Transmission probability: T(L) = 10^(-alpha * L / 10)

2. Single-Photon Detection (SNSPD):
   - Superconducting Nanowire Single-Photon Detector (SNSPD)
   - Detector quantum efficiency: eta_det = 0.85 (85%)
   - Dark count rate: D = 10 Hz (counts/sec)
   - Optical pulse repetition rate: f_rep = 50 MHz (50e6 pulses/sec)
   - Coincidence / detection time window: tau = 1 ns (1e-9 s)

3. Rates & Quantum Bit Error Rate (QBER):
   - Signal photon detection rate:
     R_sig(L) = f_rep * T(L) * eta_det
   - Dark count rate within detection gates:
     R_dark = D * tau * f_rep = 10 * 1e-9 * 50e6 = 0.50 Hz
   - QBER: Since dark counts generate completely unpolarized/random outcomes,
     they contribute to errors with probability 1/2:
     QBER(L) = (0.5 * R_dark) / (R_sig(L) + R_dark)
   - Standard security threshold for QKD protocols (BB84 / E91): 11.0%
"""

import csv
from dataclasses import dataclass, asdict
from typing import List, Dict, Any
import math


@dataclass(frozen=True)
class OpticalFiberParameters:
    wavelength_nm: float = 1550.0       # Telecom C-band
    attenuation_db_per_km: float = 0.2  # SMF-28 standard loss


@dataclass(frozen=True)
class SinglePhotonDetectorParameters:
    quantum_efficiency: float = 0.85    # SNSPD efficiency (eta)
    dark_count_rate_hz: float = 10.0    # Dark counts per second (D)
    pulse_repetition_rate_hz: float = 50e6  # 50 MHz repetition rate
    gate_window_seconds: float = 1.0e-9      # 1 ns coincidence window (tau)


@dataclass(frozen=True)
class OpticalLinkBudgetResult:
    distance_km: float
    attenuation_db: float
    transmission_prob: float
    signal_rate_hz: float
    dark_rate_hz: float
    qber_fraction: float
    qber_percentage: float
    within_security_threshold: bool  # QBER < 11%


def calculate_optical_link_budget(
    distance_km: float,
    fiber: OpticalFiberParameters = OpticalFiberParameters(),
    detector: SinglePhotonDetectorParameters = SinglePhotonDetectorParameters(),
) -> OpticalLinkBudgetResult:
    """
    Computes transmission, signal rates, dark count rates, and QBER for a single distance.
    """
    attenuation_db = fiber.attenuation_db_per_km * distance_km
    transmission_prob = 10.0 ** (-attenuation_db / 10.0)

    signal_rate = detector.pulse_repetition_rate_hz * transmission_prob * detector.quantum_efficiency
    dark_rate = detector.dark_count_rate_hz * detector.gate_window_seconds * detector.pulse_repetition_rate_hz

    total_rate = signal_rate + dark_rate
    if total_rate > 0:
        qber_fraction = (0.5 * dark_rate) / total_rate
    else:
        qber_fraction = 0.5

    qber_percentage = qber_fraction * 100.0
    within_threshold = qber_percentage <= 11.0

    return OpticalLinkBudgetResult(
        distance_km=round(distance_km, 2),
        attenuation_db=round(attenuation_db, 4),
        transmission_prob=round(transmission_prob, 8),
        signal_rate_hz=round(signal_rate, 4),
        dark_rate_hz=round(dark_rate, 4),
        qber_fraction=round(qber_fraction, 8),
        qber_percentage=round(qber_percentage, 6),
        within_security_threshold=within_threshold,
    )


def sweep_optical_link_budget(
    max_distance_km: float = 100.0,
    step_km: float = 5.0,
    fiber: OpticalFiberParameters = OpticalFiberParameters(),
    detector: SinglePhotonDetectorParameters = SinglePhotonDetectorParameters(),
) -> List[OpticalLinkBudgetResult]:
    """
    Sweeps distance from 0 to max_distance_km in increments of step_km.
    """
    results: List[OpticalLinkBudgetResult] = []
    current_dist = 0.0
    while current_dist <= max_distance_km + 1e-9:
        res = calculate_optical_link_budget(current_dist, fiber, detector)
        results.append(res)
        current_dist += step_km
    return results


def export_link_budget_csv(
    results: List[OpticalLinkBudgetResult],
    file_path: str
) -> None:
    """
    Exports link budget results to a standard CSV file matching Section 14 requirements.
    """
    fieldnames = [
        "distance_km",
        "attenuation_db",
        "transmission_prob",
        "signal_rate_hz",
        "dark_rate_hz",
        "qber_percentage",
    ]
    with open(file_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            writer.writerow({
                "distance_km": r.distance_km,
                "attenuation_db": r.attenuation_db,
                "transmission_prob": r.transmission_prob,
                "signal_rate_hz": r.signal_rate_hz,
                "dark_rate_hz": r.dark_rate_hz,
                "qber_percentage": r.qber_percentage,
            })

