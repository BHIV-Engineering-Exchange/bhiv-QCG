# COMPARATIVE BENCHMARKING REPORT
## BHQ Sovereign Quantum Computing, Photonic Systems & BioQuantum Research
### Task ID: BHQ-INFRA-001 (Phase 3 & 5 Checkpoint)

**Programme Lead:** Ganesh Vishwakarma  
**Platform Integration Lead:** Kanishk Singh  
**Trust & Instrumentation Lead:** Pritesh Patra  
**Runtime & Biological Simulation Lead:** Dhiraj & Candidate on Test Task  
**Document Identifier:** `BHQ-INFRA-001-BENCH-001`  
**Date:** 2026-11-14  

---

## 1. Executive Summary & Evaluation Methodology

In accordance with **Scientific Rules 5 & 10**:
- Every claimed advantage must be benchmarked against an established, conventional baseline under identical boundary conditions.
- Sustainability and energy expenditure must be quantified against comparable workloads.
- Experimental and numerical failures/overheads must be recorded transparently.

---

## 2. Benchmark 1: Mycelium Transport Network vs. Classical MST & Dijkstra Baseline (WS-B)

### 2.1 Problem Formulation & Baseline Definitions
- **Problem:** Connect 12 distributed nutrient/spatial demand nodes in a $100\,\text{mm} \times 100\,\text{mm}$ 2D plane.
- **Baseline 1 (Classical Minimum Spanning Tree - Kruskal):** Optimal theoretical lower bound on total wiring cost to achieve full graph connectivity ($N-1 = 11$ edges, 0 cycles).
- **Candidate Model (Mycelium Adaptive Flux Network):** Conductance-weighted flux reinforcement ($\mu = 1.2$, $\gamma = 0.35\,\text{s}^{-1}$, $dt = 0.1\,\text{s}$) followed by hyphal pruning.
- **Evaluation Criteria:**
  1. Total Wire Cost ($\sum L_{ij}$ in mm).
  2. Average Shortest Path Distance between all node pairs (latency proxy in mm).
  3. Fault Tolerance: Fraction of node pairs remaining connected after a random $20\%$ edge severance trauma (20 Monte Carlo trials).

### 2.2 Quantitative Results

| Evaluation Metric | Classical MST Baseline (Kruskal) | Mycelial Adaptive Network | Engineering Delta / Trade-off |
|:---|:---:|:---:|:---:|
| **Total Active Edges** | 11 edges ($N-1$, tree) | 11 edges (pruned mesh) | Balanced edge count |
| **Total Network Wire Length** | **$182.80\,\text{mm}$** (Optimal) | $205.65\,\text{mm}$ | $+12.50\%$ wire overhead |
| **Average Shortest Path Latency** | $67.86\,\text{mm}$ | **$63.83\,\text{mm}$** | **$-5.94\%$ latency reduction** |
| **Fault Tolerance (20% Cut Survival)** | $40.80\%$ pairwise connectivity | **$56.10\%$ pairwise connectivity** | **$+37.54\%$ resilience advantage** |
| **Redundancy Loops / Cycles** | 0 (Single point of failure) | Closed loops along primary trunks | Self-healing topology |

### 2.3 Scientific Finding & Rule 3 Adherence
The mycelium-inspired heuristic pays a modest **$+12.5\%$ wiring penalty** to achieve a **$+37.54\%$ improvement in network survivability** under edge severance, while reducing transit latency by **$5.94\%$**. 
*Crucial Boundary:* This confirms nature-inspired structural optimization, **not quantum computational supremacy**. The underlying signaling remains classical ionic transport (+44.23 mV action potential at $2.5\,\text{mm/s}$).

---

## 3. Benchmark 2: Photonic Superdense Coding vs. Classical Baseband Transmission (WS-C)

### 3.1 Protocol & Baseline Setup
- **Baseline:** Classical serial transmission of 2 bits ($b_1 b_0 \in \{"00", "01", "10", "11"\}$) requiring 2 sequential physical optical pulses.
- **Candidate Model:** Remediated Quantum Superdense Coding on `AerSimulator` transmitting 2 classical bits using 1 Bell-state entangled qubit ($q_0$).

### 3.2 Quantitative Results

| Classical Input ($b_1 b_0$) | Alice Encoding Gate on $q_0$ | Received Decoded Bitstring | Total Shots on `AerSimulator` | Dominant Decoded Count | Fidelity |
|:---:|:---:|:---:|:---:|:---:|:---:|
| `"00"` | Identity $I$ | `"00"` | 1000 | 1000 | **100.0%** |
| `"01"` | Phase-Flip $Z$ | `"01"` | 1000 | 1000 | **100.0%** |
| `"10"` | Bit-Flip $X$ | `"10"` | 1000 | 1000 | **100.0%** |
| `"11"` | Both $X \to Z$ | `"11"` | 1000 | 1000 | **100.0%** |

### 3.3 Optical Link Budget Sweep Across Distance

| Distance $L$ (km) | Channel Loss (dB) | Transmission ($T$) | Signal Rate (Hz) | QBER (%) | Tolerable ($\text{QBER} < 11\%$) |
|:---:|:---:|:---:|:---:|:---:|:---:|
| $0\,\text{km}$ | $0.0\,\text{dB}$ | $1.000$ | $4.25 \times 10^7$ | $0.000001\%$ | **PASS** |
| $20\,\text{km}$ | $4.0\,\text{dB}$ | $0.398$ | $1.69 \times 10^7$ | $0.000001\%$ | **PASS** |
| $40\,\text{km}$ | $8.0\,\text{dB}$ | $0.158$ | $6.74 \times 10^6$ | $0.000004\%$ | **PASS** |
| $60\,\text{km}$ | $12.0\,\text{dB}$ | $0.063$ | $2.68 \times 10^6$ | $0.000009\%$ | **PASS** |
| $80\,\text{km}$ | $16.0\,\text{dB}$ | $0.025$ | $1.07 \times 10^6$ | $0.000023\%$ | **PASS** |
| $100\,\text{km}$ | $20.0\,\text{dB}$ | $0.010$ | $4.25 \times 10^5$ | $0.000059\%$ | **PASS** |

---

## 4. Benchmark 3: Cryogenic Readout Chain vs. Room-Temperature Amplification (WS-D)

### 4.1 Signal Chain Noise Comparison
- **Baseline:** Direct amplification at room temperature ($T = 300\,\text{K}$).
- **Candidate Model:** 3-stage Friis cascade (TWPA at $12.5\,\text{mK}$ + HEMT at $4.0\,\text{K}$ + Room-temp LNA at $300\,\text{K}$) with $80\,\text{dB}$ net gain.

### 4.2 Quantitative Results

| Signal Chain Configuration | Total Power Gain | Effective System Noise Temperature ($T_{\text{sys}}$) | Output Demodulated $V_{\text{pp}}$ | Thermal Photon Occupancy ($n_{\text{th}}$) |
|:---|:---:|:---:|:---:|:---:|
| **Room-Temperature Direct Amp Baseline** | $80.0\,\text{dB}$ | $300.00\,\text{K}$ (Overwhelms transmon) | Corrupted by noise | $n_{\text{th}} \approx 1249.7$ (Qubit destroyed) |
| **BHQ Friis Cascade Specification** | **$80.00\,\text{dB}$** | **$0.1402\,\text{K}$** (Quantum-limited) | **$22.03\,\text{mV}_{\text{pp}}$** across $50\,\Omega$ | **$3.79 \times 10^{-11}$** (Purity preserved) |
| **Performance Margin** | Target: $80 \pm 2\,\text{dB}$ | Requirement: $< 4.0\,\text{K}$ | Standard ADC Target: $\approx 20\text{--}25\,\text{mV}$ | Threshold: $< 1.0 \times 10^{-3}$ |

### 4.3 Timing Synchronization Benchmark

| Synchronization Architecture | Clock Skew ($\Delta t_{\text{skew}}$) | Total Jitter ($\sigma_{\text{jitter}}$) | Determinism Guarantee |
|:---|:---:|:---:|:---:|
| **Standard Network NTP Baseline** | $1.0\text{--}10.0\,\text{ms}$ | $> 1.0\,\text{ms}$ | Non-deterministic, software-switched |
| **Commercial IEEE-1588 PTP (Software)** | $10.0\text{--}100.0\,\text{ns}$ | $\sim 50.0\,\text{ns}$ | Insufficient for transmon qubit gate pulses |
| **BHQ White Rabbit over SyncE Spec** | **$6.20\,\text{ps}$** | **$4.416\,\text{ps}$** | **Hardware-locked PHY layer ($\ll 100\,\text{ps}$)** |

---

## 5. Comparative Energy & Sustainability Assessment (Rule 5)

| System Under Evaluation | Primary Energy Mechanism | Wall-Plug Power Draw | Computational / Functional Output | Energy Efficiency Metric |
|:---|:---|:---:|:---|:---:|
| **Classical Computing Server (Dual Xeon)** | Electronic transistor switching ($14\,\text{nm}$) | $\sim 450\,\text{W}$ | $10^9$ FLOP/s routing updates | $\sim 2.2 \times 10^6\,\text{FLOP/Joule}$ |
| **Superconducting QPU Dilution Refrigerator**| Pulse-tube compressor + He circulation pumps | $\sim 12,000\,\text{W}$ ($12\,\text{kW}$) | 24-qubit quantum state simulation | Highly power-intensive; only justified if quantum advantage is proven |
| **Biological Fungal Culture (Mycelium)** | Substrate biochemical metabolism | $\sim 0.0005\,\text{W}$ ($0.5\,\text{mW}$) | Self-assembling transport mesh | Extremely energy-frugal, but slow ($v_{\text{prop}} \sim 2.5\,\text{mm/s}$) |
| **Ambient RF Harvester Candidate** | Ambient electromagnetic rectification | $+0.00001\,\text{W}$ ($10\,\mu\text{W}$) | Passive trickle-charging for remote sensor | Harvester net-zero or negative if ambient $P_{\text{density}} < -20\,\text{dBm}$ |
