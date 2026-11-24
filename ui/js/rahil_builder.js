/**
 * rahil_builder.js — Circuit Builder, Templates & Configuration Module
 * Owned by Rahil (UI/UX Input Lead)
 * Coordinated by Kanishk Singh
 */

const TEMPLATES = {
    bell: {
        name: "Bell State (|Φ+>)",
        qubits: 2,
        qasm: `OPENQASM 3.0;
include "stdgates.inc";
qubit[2] q;
bit[2] c;

// Prepare maximally entangled Bell state (|00> + |11>) / sqrt(2)
h q[0];
cx q[0], q[1];

// Measure both qubits
c[0] = measure q[0];
c[1] = measure q[1];`
    },
    ghz: {
        name: "3-Qubit GHZ State",
        qubits: 3,
        qasm: `OPENQASM 3.0;
include "stdgates.inc";
qubit[3] q;
bit[3] c;

// Prepare 3-qubit Greenberger-Horne-Zeilinger state (|000> + |111>) / sqrt(2)
h q[0];
cx q[0], q[1];
cx q[1], q[2];

// Simultaneous measurement
c = measure q;`
    },
    superdense: {
        name: "Superdense Coding (2-bit transfer)",
        qubits: 2,
        qasm: `OPENQASM 3.0;
include "stdgates.inc";
qubit[2] q;
bit[2] c;

// 1. Shared Entanglement
h q[0];
cx q[0], q[1];

// 2. Alice encodes message bits "11" using X and Z gates
x q[0];
z q[0];

// 3. Bob decodes Bell measurement
cx q[0], q[1];
h q[0];
c[0] = measure q[0];
c[1] = measure q[1];`
    }
};

const RahilBuilder = {
    selectedBackend: null,
    backendsList: [],

    init() {
        this.renderTemplates();
        this.loadBackends();
        this.bindEvents();
        this.loadTemplate("bell");
    },

    bindEvents() {
        const backendSelect = document.getElementById("backend-select");
        if (backendSelect) {
            backendSelect.addEventListener("change", (e) => this.onBackendChange(e.target.value));
        }

        const qasmEditor = document.getElementById("qasm-editor");
        if (qasmEditor) {
            qasmEditor.addEventListener("input", () => this.validateCircuit());
        }

        const templateSelect = document.getElementById("template-select");
        if (templateSelect) {
            templateSelect.addEventListener("change", (e) => this.loadTemplate(e.target.value));
        }

        const shotsInput = document.getElementById("shots-input");
        const shotsVal = document.getElementById("shots-val");
        if (shotsInput && shotsVal) {
            shotsInput.addEventListener("input", (e) => {
                shotsVal.textContent = e.target.value;
            });
        }
    },

    async loadBackends() {
        const select = document.getElementById("backend-select");
        const data = await QCG_API.getBackends();
        this.backendsList = data.backends || [];

        if (select) {
            select.innerHTML = "";
            this.backendsList.forEach((b) => {
                const opt = document.createElement("option");
                opt.value = b.id;
                opt.textContent = `${b.name} (${b.num_qubits}Q) — ${b.provider} [${b.status}]`;
                select.appendChild(opt);
            });

            if (this.backendsList.length > 0) {
                this.onBackendChange(this.backendsList[0].id);
            }
        }
    },

    onBackendChange(backendId) {
        this.selectedBackend = this.backendsList.find((b) => b.id === backendId) || this.backendsList[0];
        const infoEl = document.getElementById("backend-info");
        if (infoEl && this.selectedBackend) {
            const isSim = this.selectedBackend.is_simulator;
            infoEl.innerHTML = `
                <div class="flex items-center justify-between text-xs text-slate-300 mb-1">
                    <span>Provider: <strong class="text-white">${this.selectedBackend.provider}</strong></span>
                    <span class="px-2 py-0.5 rounded text-[10px] font-mono ${isSim ? 'bg-indigo-900 text-indigo-200' : 'bg-emerald-900 text-emerald-200'}">
                        ${isSim ? 'SIMULATOR' : 'LIVE QPU'}
                    </span>
                </div>
                <div class="text-[11px] text-slate-400">
                    Max Qubits: <strong class="text-indigo-400">${this.selectedBackend.num_qubits}</strong> | 
                    Pending Queue: <strong>${this.selectedBackend.pending_jobs || 0} jobs</strong>
                </div>
                <div class="text-[10px] text-slate-500 mt-1 truncate">
                    Basis: ${(this.selectedBackend.basis_gates || []).slice(0, 6).join(", ")}...
                </div>
            `;
        }
        this.validateCircuit();
    },

    renderTemplates() {
        const select = document.getElementById("template-select");
        if (!select) return;
        select.innerHTML = '<option value="">-- Load a Circuit Template --</option>';
        Object.entries(TEMPLATES).forEach(([key, t]) => {
            const opt = document.createElement("option");
            opt.value = key;
            opt.textContent = `${t.name} (${t.qubits} Qubits)`;
            select.appendChild(opt);
        });
    },

    loadTemplate(templateKey) {
        if (!templateKey || !TEMPLATES[templateKey]) return;
        const t = TEMPLATES[templateKey];
        const editor = document.getElementById("qasm-editor");
        if (editor) {
            editor.value = t.qasm;
            this.validateCircuit();
        }
    },

    validateCircuit() {
        const editor = document.getElementById("qasm-editor");
        const warningEl = document.getElementById("circuit-warning");
        const submitBtn = document.getElementById("dispatch-btn");
        if (!editor || !warningEl) return;

        const code = editor.value;
        // Simple regex to extract qubit[N] or qubit declaration
        const qubitMatch = code.match(/qubit\[(\d+)\]/) || code.match(/qreg\s+q\[(\d+)\]/);
        const requiredQubits = qubitMatch ? parseInt(qubitMatch[1], 10) : 2;

        const maxQubits = this.selectedBackend ? this.selectedBackend.num_qubits : 30;

        if (requiredQubits > maxQubits) {
            warningEl.classList.remove("hidden");
            warningEl.textContent = `⚠️ Circuit requires ${requiredQubits} qubits, but ${this.selectedBackend.name} only supports ${maxQubits} qubits!`;
            if (submitBtn) submitBtn.disabled = true;
        } else {
            warningEl.classList.add("hidden");
            if (submitBtn) submitBtn.disabled = false;
        }
        return requiredQubits;
    },

    buildSubmissionPayload() {
        const editor = document.getElementById("qasm-editor");
        const shotsInput = document.getElementById("shots-input");
        const optSelect = document.getElementById("opt-level-select");
        const resilienceSelect = document.getElementById("resilience-select");
        const fallbackCheck = document.getElementById("fallback-check");

        const qasmPayload = editor ? editor.value : "";
        const shots = shotsInput ? parseInt(shotsInput.value, 10) : 1024;
        const optLevel = optSelect ? parseInt(optSelect.value, 10) : 2;
        const resLevel = resilienceSelect ? parseInt(resilienceSelect.value, 10) : 1;
        const allowFallback = fallbackCheck ? fallbackCheck.checked : true;

        const qubits = this.validateCircuit() || 2;
        const isLiveRequested = this.selectedBackend ? !this.selectedBackend.is_simulator : false;

        return {
            workload: {
                workload_id: `wl-${Date.now()}`,
                circuit_format: "OPENQASM_3",
                qasm_payload: qasmPayload
            },
            workload_type: "QUANTUM",
            problem_size: qubits,
            shots: shots,
            seed: 42,
            target_provider: this.selectedBackend ? this.selectedBackend.provider : "Local Host",
            target_backend: this.selectedBackend ? this.selectedBackend.name : "aer_simulator",
            execution_options: {
                optimization_level: optLevel,
                resilience_level: resLevel,
                max_execution_time_seconds: 300
            },
            routing_flags: {
                requires_live_hardware: isLiveRequested,
                requires_entanglement: true,
                classical_fallback_acceptable: allowFallback
            }
        };
    }
};

window.RahilBuilder = RahilBuilder;
