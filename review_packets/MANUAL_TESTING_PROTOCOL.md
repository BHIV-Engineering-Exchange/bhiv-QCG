# 📋 QCG QUANTUM STUDIO — MANUAL ACCEPTANCE TESTING PROTOCOL
**Standard:** Gov-OS Core Compliance & SETU Architecture v6.0  
**Target Build:** QCG Quantum Execution & Provenance Studio (`web_server.py` on Port 8080)  
**Lead Integrator:** Kanishk Singh  
**QA / Manual Tester:** Sam  
**Date:** November 28, 2026  
**Environment:** `http://localhost:8080/studio/` (Local / LAN: `http://10.137.139.56:8080/studio/`)  

---

## 1. Scope & Objective
To perform a complete manual acceptance walk-through of the integrated Quantum Execution & Provenance Studio. The goal is to verify that circuit authoring, AST validation, execution routing, Little-Endian measurement frequency distributions, and cryptographic provenance operate deterministically with zero unhandled exceptions.

---

## 2. Manual Test Matrix

| Case ID | Feature / Flow | Action / Test Input | Expected Result | Verdict | Notes / Discrepancy |
| :---: | :--- | :--- | :--- | :---: | :--- |
| **TC-01** | **Happy Path: Bell State** | 1. Select "Bell State (\|Φ+⟩)" template.<br>2. Shots: 1024.<br>3. Click "DISPATCH TO QUANTUM RUNTIME". | • Dispatch button shows loading spinner.<br>• Completes in < 2.0s.<br>• Histogram displays $\approx 50\%$ `00` and $\approx 50\%$ `11`.<br>• Execution ID and Merkle root populate. | **PENDING SAM** | |
| **TC-02** | **Little-Endian Tooltip Check** | Hover cursor over `|00⟩` and `|11⟩` bars on the histogram. | Tooltip explicitly displays:<br>`Qubit Map (Little-Endian): q[0]=..., q[1]=...`<br>Confirming $q_0$ is the rightmost bit. | **PENDING SAM** | |
| **TC-03** | **3-Qubit GHZ State** | 1. Select "3-Qubit GHZ State" template.<br>2. Click "DISPATCH". | Histogram renders dominant outcomes at `000` ($\approx 50\%$) and `111` ($\approx 50\%$). Outcomes badge = `2`. | **PENDING SAM** | |
| **TC-04** | **Superdense Coding** | 1. Select "Superdense Coding" template.<br>2. Click "DISPATCH". | Encoded message `11` executes with dominant peak at `11` ($>95\%$). | **PENDING SAM** | |
| **TC-05** | **Syntax Error Boundary (Negative Test)** | 1. Enter malformed code: `invalid_syntax; gate q[0];`<br>2. Click "DISPATCH". | Red error banner appears at top with explicit OpenQASM parser error (HTTP 422). Zero unhandled crashes. | **PENDING SAM** | |
| **TC-06** | **Hardware Capacity Boundary Check** | In editor, change `qubit[2] q;` to `qubit[35] q;` (exceeds 30-qubit limit). | Yellow warning box appears: *"⚠️ Circuit requires 35 qubits, but aer_simulator only supports 30 qubits!"* Dispatch button disabled. | **PENDING SAM** | |
| **TC-07** | **Data Export (CSV & JSON)** | 1. After successful run, click "📥 CSV".<br>2. Click "💾 JSON". | • `qcg_measurement_<exec_id>.csv` downloads with valid columns.<br>• `qcg_execution_<exec_id>.json` downloads full raw payload. | **PENDING SAM** | |
| **TC-08** | **5-Step Chain Integrity & Copy** | 1. Inspect Chain Integrity card in Panel 3.<br>2. Click `📋 Copy` buttons on Trace ID, Execution ID, Leaf Hash, and Merkle Root. | • All 5 checks show green `[PASS]` badges.<br>• Copy buttons flash `✓` and text is copied to clipboard. | **PENDING SAM** | |
| **TC-09** | **Certificate Inspector Modal** | 1. Click "📜 Inspect Cryptographic Merkle Certificate".<br>2. Click "📋 Copy Certificate JSON".<br>3. Click "Done". | Modal pops up with formatted cryptographic JSON proof, copy button works, and modal closes cleanly. | **PENDING SAM** | |

---

## 3. Execution Sign-Off
* **Platform Lead Sign-Off:** Kanishk Singh (`VERIFIED_READY`)
* **Manual QA Tester Sign-Off:** Sam (`_______________________`)
* **Date of Testing:** November 28, 2026
