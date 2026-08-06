import os
import uvicorn
from fastapi import FastAPI

# Import the core QCG Gateway
from web_server import app as qcg_app

# Import the external runtime node
from external_runtime_server import app as runtime_app
from external_platform_agent import app as agent_app

# Create a unified root app
app = FastAPI(
    title="TANTRA QCG & Universal Solver Fabric (Monolith)",
    description="Unified platform serving both the Core QCG Gateway and the External Quantum Node.",
    version="1.0.0"
)

# Namespace the QCG Gateway endpoints
app.mount("/qcg", qcg_app)

# Combine and namespace the External Node endpoints
external_app = FastAPI(title="External Quantum Node")
external_app.include_router(runtime_app.router)
external_app.include_router(agent_app.router)

app.mount("/external", external_app)

@app.get("/")
async def root():
    return {
        "service": "TANTRA QCG & USF Monolith",
        "status": "ONLINE",
        "available_namespaces": {
            "Core Gateway": "/qcg",
            "External Node Plugin": "/external"
        },
        "key_endpoints": [
            "GET  /qcg/health - QCG Platform Health",
            "POST /qcg/verify - QCG Contract Verification",
            "POST /external/execute - External Node Execution",
            "POST /external/platform/integrate - External Node USF Integration"
        ]
    }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"=========================================================")
    print(f"   TANTRA Monolith Service starting on 0.0.0.0:{port}")
    print(f"=========================================================\n")
    uvicorn.run(app, host="0.0.0.0", port=port)
