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
    env_name="verilog-rtl-simulation-repair",
    max_concurrent_envs=1,
)

from fastapi.responses import HTMLResponse
import os
import subprocess

@app.get("/verify/{task_id}")
async def verify_task(task_id: str, mode: str = "broken"):
    """Live simulator verification endpoint (Compiler + Executor + Scorer)."""
    base_dir = f"server/tasks/{task_id}"
    sim_bin = f"/tmp/{task_id}_{mode}_sim"
    v_file = "broken.v" if mode == "broken" else "correct.v"
    
    totals = {"easy": 5, "medium": 10, "hard": 20}
    try:
        # STEP 1: Compilation
        cmd = ["iverilog", "-o", sim_bin, f"{base_dir}/{v_file}", f"{base_dir}/testbench.v"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return {"status": "error", "compile_error": result.stderr, "score": 0.0}
        
        # STEP 2: Execution
        sim_res = subprocess.run(["vvp", sim_bin], capture_output=True, text=True)
        stdout = sim_res.stdout
        passed = 0  # Default to 0 — must be earned

        # All testbenches print: "SIMULATION_DONE failed=N"
        if "SIMULATION_DONE" in stdout:
            try:
                failed_count = int(stdout.split("failed=")[1].split()[0])
                passed = totals[task_id] - failed_count
            except: pass
        else:
            # Fallback: count PASS lines
            passed = stdout.count(": PASS")

        score = round((passed / totals[task_id]) * 0.7 + 0.2, 2)
        
        return {
            "status": "success" if passed == totals[task_id] else "logic_error",
            "compile_error": "✅ Compiled OK" if passed == totals[task_id] else "✅ Compiled OK, but LOGIC FAILED!",
            "sim_output": sim_res.stdout,
            "passed": passed, "total": totals[task_id],
            "score": round(score, 2),
            "mode": mode
        }
    except Exception as e:
        return {"status": "error", "compile_error": str(e), "score": 0.0}

@app.get("/", response_class=HTMLResponse)
def read_root():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>RTLRepair | Interactive Debugger</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&family=JetBrains+Mono&display=swap" rel="stylesheet">
        <style>
            :root { --p: #6366f1; --bg: #0b0f1a; --c: #161b2c; --t: #f8fafc; --acc: #38bdf8; --g: #4ade80; --r: #fb7185; }
            body { background: var(--bg); color: var(--t); font-family: 'Inter', sans-serif; margin: 0; padding: 2rem; }
            .hero { text-align: center; margin-bottom: 4rem; }
            h1 { font-size: 3rem; font-weight: 800; color: var(--acc); margin: 0; }
            
            .task-panel { background: var(--c); border: 1px solid rgba(255,255,255,0.1); border-radius: 2rem; padding: 2.5rem; margin-bottom: 3rem; }
            .task-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem; }
            .btn-run { background: rgba(255,255,255,0.1); color: white; border: 1px solid rgba(255,255,255,0.2); padding: 0.6rem 1.2rem; border-radius: 0.8rem; cursor: pointer; font-weight: 700; transition: 0.2s; margin-left: 0.5rem; }
            .btn-solve { background: var(--p); color: white; border: none; padding: 0.6rem 1.2rem; border-radius: 0.8rem; cursor: pointer; font-weight: 700; transition: 0.2s; }
            .btn-run:hover, .btn-solve:hover { transform: scale(1.05); filter: brightness(1.1); }
            
            .diff-view { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-top: 1.5rem; }
            .code-box { background: #000; border-radius: 1rem; padding: 1.5rem; font-family: 'JetBrains Mono', monospace; font-size: 0.85rem; position: relative; border: 1px solid rgba(255,255,255,0.05); }
            .code-box h4 { position: absolute; top: 0.5rem; right: 1rem; margin: 0; font-size: 0.7rem; opacity: 0.5; color: var(--acc); }
            .tag-wrong { color: var(--r); } .tag-fixed { color: var(--g); }
            
            .live-output { background: #05070a; border: 1px solid #222; border-radius: 1rem; padding: 1.5rem; margin-top: 2rem; display: none; font-family: 'JetBrains Mono'; font-size: 0.8rem; }
            .log-msg { color: var(--r); white-space: pre-wrap; }
        </style>
    </head>
    <body>
        <div class="hero">
            <h1>🛠️ RTLRepair Platform</h1>
            <p style="opacity: 0.6;">Interactive Hardware Bug Diagnosis & Automated Repair Benchmark</p>
        </div>

        <!-- EASY TASK -->
        <div class="task-panel">
            <div class="task-header">
                <div>
                    <h2 style="margin:0">Level 01: 4-bit Synchronous Counter</h2>
                    <p style="opacity: 0.6; margin: 0.3rem 0;">Syntax & Port Sensitivities</p>
                </div>
                <div>
                    <button class="btn-run" onclick="runTest('easy', 'broken')">▶ Test Broken</button>
                    <button class="btn-solve" onclick="runTest('easy', 'fixed')">🚀 Verify Solution</button>
                </div>
            </div>
            
            <div class="diff-view">
                <div class="code-box"><h4>BROKEN MODULE</h4><code>always @(posedge <span class="tag-wrong">cllk</span>) begin<br>&nbsp;&nbsp;if (<span class="tag-wrong">resett</span>) count <= 0;</code></div>
                <div class="code-box"><h4>REPAIRED MODULE</h4><code>always @(posedge <span class="tag-fixed">clk</span>) begin<br>&nbsp;&nbsp;if (<span class="tag-fixed">reset</span>) count <= 0;</code></div>
            </div>
            <div id="out-easy" class="live-output"></div>
        </div>

        <!-- MEDIUM TASK -->
        <div class="task-panel">
            <div class="task-header">
                <div>
                    <h2 style="margin:0">Level 02: 4-bit ALU Unit</h2>
                    <p style="opacity: 0.6; margin: 0.3rem 0;">Behavioral Arithmetic Logic</p>
                </div>
                <div>
                    <button class="btn-run" onclick="runTest('medium', 'broken')">▶ Test Broken</button>
                    <button class="btn-solve" onclick="runTest('medium', 'fixed')">🚀 Verify Solution</button>
                </div>
            </div>
            
            <div class="diff-view">
                <div class="code-box"><h4>BROKEN MODULE</h4><code>SUB: res = a <span class="tag-wrong">+</span> b;<br>AND: res = a <span class="tag-wrong">|</span> b;</code></div>
                <div class="code-box"><h4>REPAIRED MODULE</h4><code>SUB: res = a <span class="tag-fixed">-</span> b;<br>AND: res = a <span class="tag-fixed">&</span> b;</code></div>
            </div>
            <div id="out-medium" class="live-output"></div>
        </div>

        <!-- HARD TASK -->
        <div class="task-panel">
            <div class="task-header">
                <div>
                    <h2 style="margin:0">Level 03: Traffic Light FSM</h2>
                    <p style="opacity: 0.6; margin: 0.3rem 0;">Finite State Machine Transitions</p>
                </div>
                <div>
                    <button class="btn-run" onclick="runTest('hard', 'broken')">▶ Test Broken</button>
                    <button class="btn-solve" onclick="runTest('hard', 'fixed')">🚀 Verify Solution</button>
                </div>
            </div>
            
            <div class="diff-view">
                <div class="code-box"><h4>BROKEN MODULE</h4><code>GREEN: if (timer > 50) <span class="tag-wrong">state_next = RED;</span></code></div>
                <div class="code-box"><h4>REPAIRED MODULE</h4><code>GREEN: if (timer > 50) <span class="tag-fixed">state_next = YELLOW;</span></code></div>
            </div>
            <div id="out-hard" class="live-output"></div>
        </div>

        <script>
            async function runTest(tid, mode) {
                const out = document.getElementById(`out-${tid}`);
                out.style.display = "block";
                out.innerHTML = `<span style='color: var(--acc)'>⚡ ${mode === 'broken' ? 'Diagnosing Bugs...' : 'Verifying Repair...'}</span>`;
                try {
                    const res = await fetch(`/verify/${tid}?mode=${mode}`);
                    const data = await res.json();
                    let scoreHtml = `<div style="background: ${mode==='fixed' ? 'var(--g)' : 'var(--p)'}; color: ${mode==='fixed' ? '#000' : '#fff'}; display: inline-block; padding: 0.2rem 0.6rem; border-radius: 0.4rem; font-weight: 800; margin-bottom: 0.5rem;">SCORE: ${data.score}</div>`;
                    
                    if (data.status === "error") {
                        out.innerHTML = `${scoreHtml}<br><span style="color: var(--r); font-weight:800">SYSTEM REJECTED:</span><br class='log-msg'>${data.compile_error}`;
                    } else if (data.status === "logic_error") {
                        out.innerHTML = `${scoreHtml}<br><span style="color: var(--r); font-weight:800">LOGIC BUGS DETECTED:</span><br class='log-msg'>${data.compile_error}<br><small>Verified ${data.passed}/${data.total} test vectors.</small>`;
                    } else {
                        out.innerHTML = `${scoreHtml}<br><span style="color: var(--g); font-weight:800">✅ BENCHMARK PASSED!</span><br><small>All tests passed. Final reward reached.</small>`;
                    }
                } catch (e) {
                    out.innerHTML = "Backend Timeout - Check Logs";
                }
            }
        </script>
    </body>
    </html>
    """

def main():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)

if __name__ == "__main__":
    main()