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

from fastapi.responses import HTMLResponse

@app.get("/", response_class=HTMLResponse)
def read_root():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Verilog-RTL-Simulation-Repair | Dashboard</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&family=JetBrains+Mono&display=swap" rel="stylesheet">
        <style>
            :root {
                --primary: #6366f1;
                --bg: #0f172a;
                --card: #1e293b;
                --text: #f8fafc;
                --accent: #38bdf8;
            }
            body { 
                background: var(--bg); 
                color: var(--text); 
                font-family: 'Inter', sans-serif;
                margin: 0;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
            }
            .container {
                background: var(--card);
                padding: 3rem;
                border-radius: 1.5rem;
                box-shadow: 0 25px 50px -12px rgba(0,0,0,0.5);
                border: 1px solid rgba(255,255,255,0.1);
                max-width: 600px;
                width: 90%;
            }
            h1 { font-weight: 800; font-size: 2.2rem; margin-bottom: 0.5rem; color: var(--accent); }
            p { opacity: 0.8; font-size: 1.1rem; line-height: 1.6; }
            .status {
                display: inline-flex;
                align-items: center;
                background: rgba(34, 197, 94, 0.2);
                color: #4ade80;
                padding: 0.5rem 1rem;
                border-radius: 9999px;
                font-weight: 600;
                margin-top: 1rem;
            }
            .status::before {
                content: "";
                display: inline-block;
                width: 10px;
                height: 10px;
                background: #4ade80;
                border-radius: 50%;
                margin-right: 0.75rem;
                box-shadow: 0 0 10px #4ade80;
            }
            .grid {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 1.5rem;
                margin-top: 2rem;
            }
            .stat-card {
                background: rgba(15, 23, 42, 0.5);
                padding: 1.25rem;
                border-radius: 1rem;
                border: 1px solid rgba(255,255,255,0.05);
            }
            .stat-value { font-family: 'JetBrains Mono', monospace; font-size: 1.2rem; color: var(--accent); }
            .footer { margin-top: 2rem; font-size: 0.9rem; opacity: 0.5; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 1.5rem; }
            a { color: var(--accent); text-decoration: none; font-weight: 600; }
            a:hover { text-decoration: underline; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🛠️ Verilog-RTL Repair</h1>
            <p>The first automated simulation repair environment for AI hardware agents.</p>
            <div class="status">ENVIRONMENT LIVE</div>
            
            <div class="grid">
                <div class="stat-card">
                    <div style="font-size: 0.8rem; margin-bottom: 0.4rem; opacity: 0.6;">API TYPE</div>
                    <div class="stat-value">OpenEnv/WS</div>
                </div>
                <div class="stat-card">
                    <div style="font-size: 0.8rem; margin-bottom: 0.4rem; opacity: 0.6;">TASKS</div>
                    <div class="stat-value">3 Levels</div>
                </div>
                <div class="stat-card">
                    <div style="font-size: 0.8rem; margin-bottom: 0.4rem; opacity: 0.6;">SIMULATOR</div>
                    <div class="stat-value">iverilog v11</div>
                </div>
                <div class="stat-card">
                    <div style="font-size: 0.8rem; margin-bottom: 0.4rem; opacity: 0.6;">AVERAGE RECO</div>
                    <div class="stat-value">0.43 score</div>
                </div>
            </div>

            <div class="footer">
                Ready for evaluation. Visit <a href="/docs">/docs</a> for Swager UI.
            </div>
        </div>
    </body>
    </html>
    """

def main():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)

if __name__ == "__main__":
    main()