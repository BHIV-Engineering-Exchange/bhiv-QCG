/**
 * app.js — Main Application State & Module Coordinator
 * Standard: SETU OS Architecture v6.0
 * Owned by Kanishk Singh (Integration Lead)
 */

document.addEventListener("DOMContentLoaded", async () => {
    console.log("⚛️ Initializing QCG Quantum Execution & Provenance Studio...");

    // 1. Initialize Sub-modules
    if (window.RahilBuilder) window.RahilBuilder.init();
    if (window.GauriResults) window.GauriResults.init();

    // 2. Bind Dispatch Handler
    const dispatchBtn = document.getElementById("dispatch-btn");
    if (dispatchBtn) {
        dispatchBtn.addEventListener("click", handleDispatch);
    }

    // 3. Initial Health Check
    try {
        const health = await QCG_API.getHealth();
        const healthBadge = document.getElementById("health-badge");
        if (healthBadge) {
            if (health.status === "UP" || health.status === "OK") {
                healthBadge.className = "px-2 py-0.5 rounded text-[10px] bg-emerald-950 text-emerald-300 border border-emerald-800";
                healthBadge.textContent = "GATEWAY: ONLINE (8080)";
            } else {
                healthBadge.className = "px-2 py-0.5 rounded text-[10px] bg-amber-950 text-amber-300 border border-amber-800";
                healthBadge.textContent = "GATEWAY: DEGRADED";
            }
        }
    } catch (e) {
        console.warn("Health check unreachable:", e);
    }
});

async function handleDispatch() {
    const errorBanner = document.getElementById("error-banner");
    if (errorBanner) errorBanner.classList.add("hidden");

    try {
        const payload = RahilBuilder.buildSubmissionPayload();
        console.log("Dispatching workload payload:", payload);

        GauriResults.setLoading(true, "Transpiling and Submitting to Quantum Runtime...");

        const result = await QCG_API.submitCircuit(payload);
        console.log("Submission response received:", result);

        // Check if asynchronous job returned
        if (result.status === "QUEUED" && result.job_id) {
            GauriResults.setLoading(true, `Job Queued on ${result.target_backend} (Position: ${result.queue_position || 1}). Polling...`);
            
            // Poll for completion
            let finished = false;
            let attempts = 0;
            while (!finished && attempts < 30) {
                await new Promise((r) => setTimeout(r, 2000));
                attempts++;
                const pollResp = await QCG_API.pollJob(result.job_id);
                if (pollResp.status === "DONE" || pollResp.status === "SUCCESS") {
                    GauriResults.renderResults(pollResp);
                    finished = true;
                    return;
                }
            }
        }

        // Synchronous / immediate completion
        GauriResults.renderResults(result);

    } catch (err) {
        console.error("Dispatch error:", err);
        GauriResults.setLoading(false);
        if (errorBanner) {
            errorBanner.classList.remove("hidden");
            errorBanner.textContent = `Error: ${err.message || "Execution failed. Check backend connectivity."}`;
        }
    }
}
