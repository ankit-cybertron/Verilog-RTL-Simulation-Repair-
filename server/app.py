"""
app.py — FastAPI server entry point for RTLRepair-Env

Exposes the environment via OpenEnv's create_app() utility,
which registers /reset, /step, /state, and /ws WebSocket endpoints.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openenv.core.env_server import create_app
from server.environment import RTLRepairEnvironment
from models import RTLAction, RTLObservation

app = create_app(
    RTLRepairEnvironment,
    RTLAction,
    RTLObservation,
    env_name="rtlrepair_env",
    max_concurrent_envs=1,
)

@app.get("/")
def read_root():
    return {
        "status": "online",
        "project": "Verilog-RTL-Simulation-Repair",
        "description": "OpenEnv environment for AI-assisted Hardware Debugging",
        "docs": "/docs"
    }

def main():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)

if __name__ == "__main__":
    main()