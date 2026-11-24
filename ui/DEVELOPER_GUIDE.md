# ⚛️ QCG Quantum Studio — Frontend Developer Guide
## Written for UI/UX Engineers (Rahil & Gauri)
**Integration Lead:** Kanishk Singh | **Backend Standard:** Gov-OS & SETU OS v6.0

Welcome Rahil & Gauri! You **do NOT need a degree in quantum physics** to build this UI. From a web application perspective, quantum computing is just a specialized client-server flow.

---

## 1. The 30-Second Mental Model

Think of a Quantum Computer like a specialized **GPU cluster**:

```
[ FRONTEND UI ]                      [ QCG GATEWAY (:8080) ]               [ QUANTUM BACKEND ]
1. Pick Machine (Dropdown)   ----->   GET /quantum/backends       ----->   IBM QPU or Aer Simulator
2. Submit Circuit Code (QASM) ----->  POST /hybrid/submit         ----->   Executes Circuit 1024 times
3. Show Histogram & Receipt  <-----   Measurement Counts + Hashes <-----   Returns Probability Distribution
```

1. **Backend / QPU**: Like selecting a GPU. A machine has a capacity of **Qubits** (e.g. 5, 30, or 127). The user cannot run an 8-qubit job on a 5-qubit machine.
2. **OpenQASM 3.0**: Think of it like SQL or Python for quantum. It's just a text string sent to the backend. We give users one-click templates (Bell State, GHZ) so they rarely need to write it from scratch.
3. **Measurement Results (Counts)**: Quantum circuits run repeatedly (e.g. 1024 "shots"). The result is simply a **frequency distribution** (e.g. `"00"` occurred 512 times, `"11"` occurred 512 times).
4. **Cryptographic Provenance**: A digital cryptographic "seal" (SHA-256 Merkle root & ECDSA signature) proving the quantum result actually came from that machine and was not faked or tampered with.

---

## 2. ⚠️ The ONLY Quantum Trap: "Little-Endian" Bit Ordering

In normal English strings, index `0` is on the **left**:
- In `"CAT"`, index 0 is `'C'`.

In Qiskit Quantum Measurement strings, index `0` is on the **RIGHT** (like binary numbers where the 1s place is on the right):
- In bitstring `"10"`:
  - **Rightmost bit (`0`)** is classical bit $c_0$ (measured from Qubit $q_0$).
  - **Leftmost bit (`1`)** is classical bit $c_1$ (measured from Qubit $q_1$).

### How Gauri Should Display This in the Histogram:
When hovering over bar `"1100"`:
```
Bitstring: 1100 (Count: 512)
Qubit 0 (Rightmost): 0
Qubit 1:             0
Qubit 2:             1
Qubit 3 (Leftmost):  1
```
*(A helper function `decodeBitstring(bits)` is already provided in `gauri_results.js` for you!)*

---

## 3. Clear Ownership: Who Builds What

### 👨‍💻 Rahil's Domain: `ui/js/rahil_builder.js` (The Input Side)
- **Backend Dropdown**: Calls `QCG_API.getBackends()`. Displays machine status (`ONLINE` / `MAINTENANCE`), queue depth, and max qubits.
- **Circuit Editor**: Text area for OpenQASM 3.0 code.
- **Template Buttons**: One-click insert for:
  - `Bell State (|Φ+>)` (2 qubits)
  - `3-Qubit GHZ State` (3 qubits)
  - `Superdense Coding` (2 qubits)
- **Qubit Capacity Guard**: If the code uses more qubits than the backend supports, disable the Submit button and show a helpful warning!
- **Submit Button**: Collects the payload and calls `QCG_API.submitCircuit(payload)`.

---

### 👩‍💻 Gauri's Domain: `ui/js/gauri_results.js` (The Output & Trust Side)
- **Job Status Tracker**: Shows progress bar while the job is `QUEUED` or `RUNNING`.
- **Measurement Histogram**: Renders a Chart.js bar chart of the resulting measurement counts (`"00"`, `"11"`, etc.).
- **Provenance Panel**: Displays:
  - `Execution ID`: e.g. `exec-77b10a2f`
  - `Deterministic Leaf Hash`: SHA-256
  - `Merkle Root`: SHA-256
  - `Trust Badge`: `[ECDSA VERIFIED]`
- **Certificate Modal**: When clicking `[ECDSA VERIFIED]`, pop open a clean modal showing the Merkle proof branch from `QCG_API.getCertificate(executionId)`.

---

## 4. API Endpoints You Are Interacting With

All network calls are pre-written in `ui/js/api.js`. You just call JavaScript functions:

| Function in `api.js` | Endpoint Called | Purpose |
|---|---|---|
| `QCG_API.getBackends()` | `GET /quantum/backends` | Get list of available simulators & IBM QPUs |
| `QCG_API.submitCircuit(payload)` | `POST /hybrid/submit` | Run or queue quantum circuit |
| `QCG_API.pollJob(jobId)` | `GET /quantum/jobs/{job_id}` | Poll asynchronous QPU jobs |
| `QCG_API.getCertificate(execId)` | `GET /evidence/certificate/{id}` | Fetch Merkle certificate & proof |

---

## 5. How to Run & Test
1. Make sure your Python server is running:
   ```bash
   python web_server.py
   ```
2. Open your browser to:
   ```
   http://localhost:8080/studio
   ```
3. Refresh the page whenever you edit your JavaScript files!
