"""
evidence/run_optical_link_budget.py
===================================
Simulates the quantum optical link budget across SMF-28 single-mode optical fiber.
Calculates attenuation, photon transmission probability, signal detection rate,
dark count rate, and QBER vs distance from 0 to 100 km.
Saves CSV evidence to evidence/03_KANISHK_OPTICAL_LINK_BUDGET.csv.
"""

import os
import sys

# Ensure project root is on sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from photonics_rf_systems.optical_link_budget import (
    OpticalFiberParameters,
    SinglePhotonDetectorParameters,
    sweep_optical_link_budget,
    export_link_budget_csv,
)


def main():
    print("[*] Running Optical Link Budget & QBER Simulation (0 - 100 km in 5 km steps)...")
    fiber = OpticalFiberParameters(wavelength_nm=1550.0, attenuation_db_per_km=0.2)
    detector = SinglePhotonDetectorParameters(
        quantum_efficiency=0.85,
        dark_count_rate_hz=10.0,
        pulse_repetition_rate_hz=50e6,
        gate_window_seconds=1.0e-9,
    )

    results = sweep_optical_link_budget(
        max_distance_km=100.0,
        step_km=5.0,
        fiber=fiber,
        detector=detector,
    )

    out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "evidence")
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "03_KANISHK_OPTICAL_LINK_BUDGET.csv")

    export_link_budget_csv(results, out_file)
    print(f"[+] Successfully exported optical link budget CSV to {out_file}")

    print("\nSummary Results Preview:")
    print(f"{'Dist (km)':<10} | {'Loss (dB)':<10} | {'Transmission':<14} | {'Signal (Hz)':<14} | {'QBER (%)':<12} | {'Tolerable (<11%)'}")
    print("-" * 80)
    for r in results:
        print(f"{r.distance_km:<10} | {r.attenuation_db:<10.1f} | {r.transmission_prob:<14.6e} | {r.signal_rate_hz:<14.2e} | {r.qber_percentage:<12.6f}% | {r.within_security_threshold}")


if __name__ == "__main__":
    main()

