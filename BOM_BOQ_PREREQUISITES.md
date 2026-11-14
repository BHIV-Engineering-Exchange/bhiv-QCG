# BOM / BOQ PREREQUISITES & DEVELOPMENT FEASIBILITY GATE
## BHQ Sovereign Quantum Computing, Photonic Systems & BioQuantum Research
### Task ID: BHQ-INFRA-001 (Phase 4 & 5 Checkpoint)

**Programme Lead:** Ganesh Vishwakarma  
**Platform Integration Lead:** Kanishk Singh  
**Trust & Instrumentation Lead:** Pritesh Patra  
**Runtime & Biological Simulation Lead:** Dhiraj & Candidate on Test Task  
**Document Identifier:** `BHQ-INFRA-001-BOM-PREREQ-001`  
**Date:** 2026-11-14  
**Hardware Procurement Status:** **STRICTLY NOT AUTHORISED (GOVERNANCE RULE 8 ENFORCED)**  

---

## 1. Governance Authority & Mandatory Procurement Policy

Under **BHQ-INFRA-001 Section 4 (Rule 8)**:
> *"No specialised hardware purchases or fabrication before requirements, feasibility, and explicit engineering approval."*

This document formalizes the mandatory technical prerequisites that **MUST BE FULLY SATISFIED** before a defensible, auditable Bill of Materials (BOM) and Bill of Quantities (BOQ) can be submitted for capital expenditure authorization.

---

## 2. Prerequisite Gates Before Procurement Authorization

Every candidate component must advance through four consecutive prerequisite gates:

```
+-------------------------------------------------------------------------------------------------------------+
|                                        BOM/BOQ PREREQUISITE GATE MODEL                                     |
+-------------------------------------------------------------------------------------------------------------+
|                                                                                                             |
|  [GATE 1: NUMERICAL & BEHAVIORAL SIMULATION CONVERGENCE]                                                    |
|  - Validated simulation model with reproducible outputs (PASSED: Friis, Attenuation, Superdense, Mycelium)  |
|  - Quantitative operating tolerance margins defined (e.g., gain 80 +/- 2 dB, noise temp < 4.0 K)           |
|                                                                                                             |
|  [GATE 2: IN-SITU PHYSICAL CHARACTERIZATION & ENVIRONMENTAL AUDIT]                                          |
|  - Ambient RF spectrum sweep (100 MHz - 6 GHz) establishing baseline field strength                         |
|  - Laboratory mechanical vibration spectrum (VC-E/VC-F floor vibration criteria)                            |
|  - 3-phase clean power stability, backup UPS, and chilled water availability (>= 15 kW cooling)             |
|                                                                                                             |
|  [GATE 3: REGULATORY, EXPORT CONTROL & SUPPLY CHAIN AUDIT]                                                  |
|  - Dual-use export control classification (ITAR / EAR / Wassenaar Arrangement for cryogenics & TWPAs)       |
|  - Minimum of 2 qualified, non-sanctioned sovereign suppliers identified for each mission-critical part     |
|                                                                                                             |
|  [GATE 4: FORMAL PROGRAMME LEAD REVIEW & SOVEREIGN SIGN-OFF]                                               |
|  - Engineering review of total lifecycle cost (TCO: CapEx + OpEx for Helium-3 and electricity)              |
|  - Explicit written sign-off from Programme Lead (Ganesh Vishwakarma)                                       |
|                                                                                                             |
+-------------------------------------------------------------------------------------------------------------+
```

---

## 3. Subsystem BOM/BOQ Prerequisites & Readiness Audit

### 3.1 Dilution Refrigerator & Cryogenic Subsystem (WS-D)
- **Candidate Components:** Dry dilution refrigerator ($10\text{--}15\,\text{mK}$ base, $\ge 400\,\mu\text{W}$ cooling at $100\,\text{mK}$), $^3\text{He}/^4\text{He}$ gas mixture ($10\text{--}15\,\text{liters}$ STP), scroll pump and turbo-molecular pumps.
- **Current Readiness:** `CONCEPTUAL DESIGN ONLY (MATURITY: LEVEL 1)`.
- **Missing Information & Prerequisites:**
  1. Exact heat load budget from total coaxial and fiber line count (must not exceed $15\,\mu\text{W}$ at $20\,\text{mK}$).
  2. Laboratory infrastructure confirmation: ceiling height ($\ge 3.8\,\text{m}$), floor load ($\ge 1200\,\text{kg/m}^2$), chilled water loop ($15\text{--}20\,\text{kW}$ heat extraction).
  3. Sovereign export control compliance for $^3\text{He}$ gas allocation and international customs licensing.

### 3.2 Microwave Readout & Precision Control Electronics (WS-C & WS-D)
- **Candidate Components:** Traveling Wave Parametric Amplifiers (TWPA, $4\text{--}8\,\text{GHz}$), High Electron Mobility Transistor (HEMT, $4\text{--}8\,\text{GHz}$, $4\,\text{K}$), multi-channel Arbitrary Waveform Generators ($\ge 1\,\text{GSa/s}$, 14-bit), digitizers, cryogenic circulators/isolators, semi-rigid NbTi and CuNi coaxial cables.
- **Current Readiness:** `SIMULATED & SPECIFIED (MATURITY: LEVEL 2)`.
- **Missing Information & Prerequisites:**
  1. TWPA pump tone power requirements and unwanted spurious generation across qubit readout frequencies.
  2. Insertion loss and phase noise calibration across cryogenic semi-rigid cabling from $300\,\text{K}$ down to $10\,\text{mK}$.
  3. Formal vendor quotes and lead-time guarantees (typically $26\text{--}40$ weeks for cryogenic low-noise amplifiers).

### 3.3 Photonic & Optical Fiber Subsystems (WS-C)
- **Candidate Components:** Superconducting Nanowire Single-Photon Detectors (SNSPD, $\ge 85\%$ efficiency at $1550\,\text{nm}$), telecom C-band continuous-wave laser diodes, electro-optic phase modulators, polarization controllers, SMF-28 optical fiber spools.
- **Current Readiness:** `SIMULATED & SPECIFIED (MATURITY: LEVEL 2)`.
- **Missing Information & Prerequisites:**
  1. Cryogenic thermal leak characterization of optical fiber hermetic feedthroughs entering the $4\,\text{K}$ and $10\,\text{mK}$ plates.
  2. Measured dark count rates of candidate SNSPDs under expected laboratory ambient background.
  3. Polarization drift rates over standard buried telecom optical conduit to determine adaptive tracking requirements.

### 3.4 Wet-Lab Biological & BioQuantum Sensing Equipment (WS-B)
- **Candidate Components:** High-density Microelectrode Array (MEA, 64–256 channel bio-potential recording), differential bio-amplifiers with low input noise ($< 1\,\mu\text{V}_{\text{rms}}$), temperature- and humidity-controlled fungal incubators, Faraday cage enclosure.
- **Current Readiness:** `CONCEPTUAL DESIGN ONLY (MATURITY: LEVEL 1)`.
- **Missing Information & Prerequisites:**
  1. Bio-safety laboratory level (BSL-1 minimum) space allocation and spore containment procedures for *Pleurotus ostreatus* cultivation.
  2. Electrical impedance match between titanium nitride (TiN) electrode tips and fungal hyphal cell walls.
  3. Signal-to-noise ratio (SNR) verification under ambient 50 Hz power-line interference.

---

## 4. Provisional Candidate Component Register

*(For Technical Feasibility and Budget Estimation Only — NO PURCHASING PERMITTED)*

| Subsystem | Candidate Component | Function | Provisional Quantity | Estimated Unit Cost (USD) | Lead Time (Weeks) | Supplier Alternatives | Prerequisite Status |
|:---|:---|:---|:---:|:---:|:---:|:---|:---:|
| **Cryogenics** | Dry Dilution Refrigerator ($10\,\text{mK}$) | Qubit cryogenic environment | 1 unit | \$600,000–\$950,000 | 36–52 | BlueFors (FI), Oxford Instruments (UK) | **GATED (Prereq 1, 2, 3 Missing)** |
| **Cryogenics** | Helium-3 / Helium-4 Gas Mixture | Cooling medium | 12 liters STP | \$35,000–\$50,000 | 12–20 | Chemgas (FR), Linde (DE) | **GATED (Export License Required)** |
| **Microwave** | Cryogenic TWPA ($4\text{--}8\,\text{GHz}$) | Quantum-limited first-stage amp | 2 units | \$25,000–\$35,000 | 20–30 | Q-Microwave (SE), Raytheon BBN (US) | **GATED (Specification Verified)** |
| **Microwave** | Cryogenic HEMT ($4\text{--}8\,\text{GHz}$, 4K)| Second-stage low-noise amp | 2 units | \$8,000–\$12,000 | 12–16 | Low Noise Factory (SE), Cosmic (US) | **GATED (Specification Verified)** |
| **Timing** | White Rabbit Master & Node Switch | Sub-10 ps timing sync | 1 master + 2 nodes| \$12,000–\$18,000 | 8–12 | Seven Solutions (ES), Creotech (PL) | **GATED (Spec Verified in Sim)** |
| **Control** | Multi-Channel AWG/Digitizer | Pulse generation & readout | 1 chassis | \$90,000–\$140,000 | 16–24 | Zurich Instruments (CH), QBlox (NL) | **GATED (Architecture Review Req)**|
| **Photonics** | Cryogenic SNSPD Dual Channel | Single-photon detection | 1 unit | \$45,000–\$70,000 | 16–20 | Single Quantum (NL), ID Quantique (CH) | **GATED (Thermal Budget Missing)** |
| **Bio-Lab** | Multi-Electrode Bio-Amp System | Hyphal action potential record | 1 unit | \$20,000–\$35,000 | 8–12 | Multichannel Systems (DE), Intan (US) | **GATED (BSL-1 Lab Missing)** |

---

## 5. Development Feasibility Recommendation

**Conclusion for Checkpoint 1:**
1. Maintain strict adherence to **Rule 8**: Under no circumstances should purchase orders or fabrication contracts be issued at this stage.
2. Advance to **Task 2 (Model Validation & Comparative Benchmarking)** and **Task 3 (System Model & Instrumentation Design)** to resolve the missing Level 1 & 2 prerequisites.
3. Prepare the preliminary BOM/BOQ only after the cryogenic thermal load budget, in-situ ambient RF measurement, and bio-safety facility are formally certified.
