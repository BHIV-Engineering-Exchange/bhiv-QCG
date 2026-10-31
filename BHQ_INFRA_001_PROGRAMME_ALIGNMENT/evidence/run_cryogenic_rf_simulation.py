"""
evidence/run_cryogenic_rf_simulation.py
=======================================
Simulates thermal photon occupation and attenuation down the dilution refrigerator stages (300 K to 10 mK).
Saves verification evidence to evidence/03_KANISHK_CRYOGENIC_RF_PROFILE.json.
"""

import os
import json
import sys
from datetime import datetime, timezone

# Ensure project root is on sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from photonics_rf_systems.cryogenic_rf_attenuation import (
    CryogenicRFLineModel,
    simulate_cryogenic_attenuation_chain,
)


def main():
    print("[*] Running Cryogenic Microwave Attenuation Profile Simulation (300 K -> 10 mK)...")
    model = CryogenicRFLineModel(qubit_frequency_ghz=5.0)
    report = simulate_cryogenic_attenuation_chain(model)

    report["timestamp_utc"] = datetime.now(timezone.utc).isoformat()
    report["engineer"] = "Kanishk Singh"
    report["role"] = "Lead Quantum Photonic Systems Engineer & Quantum Communications Protocol Architect"

    out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "evidence")
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "03_KANISHK_CRYOGENIC_RF_PROFILE.json")

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"[+] Successfully exported cryogenic RF profile to {out_file}")
    print(f"    Qubit Frequency: {report['qubit_frequency_ghz']} GHz")
    print(f"    Quantum Temperature: {report['quantum_temperature_k']} K")
    print(f"    Room Temperature n_th (300 K): {report['room_temperature_n_th']} photons")
    print(f"    Base Plate Equilibrium n_th (10 mK): {report['base_plate_equilibrium_n_th']:.2e} photons")
    print(f"    Total Coaxial Line Attenuation: {report['total_line_attenuation_db']} dB")
    print(f"    Ground State Preserved (n_th < 1e-3): {report['is_ground_state_preserved']}")


if __name__ == "__main__":
    main()

