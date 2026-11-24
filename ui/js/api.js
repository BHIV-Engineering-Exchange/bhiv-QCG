/**
 * api.js — Shared QCG API Client Layer
 * Standard: SETU OS Architecture v6.0 / Gov-OS Core Compliance
 * Owned by Kanishk Singh (Integration Lead)
 */

const QCG_API = {
    baseUrl: window.location.origin,

    /**
     * Fetch list of available quantum backends (local simulators and IBM QPUs).
     */
    async getBackends() {
        try {
            const resp = await fetch(`${this.baseUrl}/quantum/backends`);
            if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${resp.statusText}`);
            return await resp.json();
        } catch (err) {
            console.error("Failed to fetch quantum backends:", err);
            // Graceful fallback
            return {
                count: 1,
                backends: [{
                    id: "qiskit-aer-local",
                    name: "aer_simulator",
                    provider: "Local Host (AerSimulator)",
                    num_qubits: 30,
                    is_simulator: true,
                    status: "AVAILABLE",
                    pending_jobs: 0,
                    basis_gates: ["h", "x", "y", "z", "cx", "cz", "rx", "ry", "rz"]
                }]
            };
        }
    },

    /**
     * Submit a quantum or hybrid workload to QCG.
     */
    async submitCircuit(payload) {
        try {
            const resp = await fetch(`${this.baseUrl}/hybrid/submit`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            if (!resp.ok) {
                const errData = await resp.json().catch(() => ({}));
                throw new Error(errData.detail || errData.message || `HTTP ${resp.status}`);
            }
            return await resp.json();
        } catch (err) {
            console.error("Submission failed:", err);
            throw err;
        }
    },

    /**
     * Poll status of an asynchronous QPU job.
     */
    async pollJob(jobId) {
        try {
            const resp = await fetch(`${this.baseUrl}/quantum/jobs/${encodeURIComponent(jobId)}`);
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
            return await resp.json();
        } catch (err) {
            console.error(`Failed to poll job ${jobId}:`, err);
            throw err;
        }
    },

    /**
     * Retrieve verifiable Merkle execution certificate for an execution ID.
     */
    async getCertificate(executionId) {
        try {
            const resp = await fetch(`${this.baseUrl}/evidence/certificate/${encodeURIComponent(executionId)}`);
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
            return await resp.json();
        } catch (err) {
            console.error(`Failed to fetch certificate for ${executionId}:`, err);
            throw err;
        }
    },

    /**
     * Check gateway health.
     */
    async getHealth() {
        try {
            const resp = await fetch(`${this.baseUrl}/health`);
            return await resp.json();
        } catch (err) {
            return { status: "OFFLINE", error: err.message };
        }
    }
};

window.QCG_API = QCG_API;
