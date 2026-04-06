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

from fastapi import Body
from fastapi.responses import HTMLResponse
import subprocess, tempfile, re

TOTALS = {"easy": 5, "medium": 10, "hard": 20}

def _grade_verilog(task_id: str, verilog_code: str) -> dict:
    """Core grader: compiles + simulates any Verilog string against a task testbench."""
    total = TOTALS.get(task_id, 5)
    base_dir = f"server/tasks/{task_id}"
    tb_file  = f"{base_dir}/testbench.v"
    logs     = []

    with tempfile.TemporaryDirectory() as tmp:
        agent_file = os.path.join(tmp, "agent.v")
        sim_bin    = os.path.join(tmp, "sim")

        with open(agent_file, "w") as f:
            f.write(verilog_code)

        # ── Step 1: Compilation ────────────────────────────────────────────────
        logs.append("📋 STEP 1: Compiling with iverilog...")
        compile_res = subprocess.run(
            ["iverilog", "-o", sim_bin, agent_file, tb_file],
            capture_output=True, text=True, timeout=10
        )

        if compile_res.returncode != 0:
            err = compile_res.stderr.strip()
            for line in err.splitlines():
                logs.append(f"  ❌ {line}")
            error_count = len([l for l in err.splitlines() if "error" in l.lower()])
            score = max(0.0, 0.05 * (3 - error_count))
            logs.append(f"\n⚠️  Compilation FAILED — {error_count} error(s)")
            logs.append(f"📊 SCORE: {score:.2f}  (0.0 base — compile failed)")
            return {
                "status": "compile_error",
                "compile_error": err,
                "sim_output": "",
                "passed": 0,
                "total": total,
                "score": round(score, 2),
                "logs": "\n".join(logs),
                "vector_results": []
            }

        logs.append("  ✅ Compilation SUCCESS")

        # ── Step 2: Simulation ─────────────────────────────────────────────────
        logs.append("\n📋 STEP 2: Running simulation with vvp...")
        sim_res = subprocess.run(
            ["vvp", sim_bin],
            capture_output=True, text=True, timeout=10
        )
        stdout = sim_res.stdout

        # ── Step 3: Parse per-vector results ───────────────────────────────────
        logs.append("\n📋 STEP 3: Test Vector Results:")
        vector_results = []
        passed = 0

        for line in stdout.splitlines():
            if "VECTOR" in line and ("PASS" in line or "FAIL" in line):
                is_pass = "PASS" in line
                if is_pass:
                    passed += 1
                    logs.append(f"  ✅ {line.strip()}")
                else:
                    logs.append(f"  ❌ {line.strip()}")
                vector_results.append({"line": line.strip(), "passed": is_pass})

        # Parse SIMULATION_DONE if vectors weren't individually logged
        if not vector_results and "SIMULATION_DONE" in stdout:
            try:
                failed_count = int(stdout.split("failed=")[1].split()[0])
                passed = total - failed_count
                logs.append(f"  📊 Parsed from summary: {passed}/{total} passed")
            except:
                passed = 0

        # Fallback
        if not vector_results and "SIMULATION_DONE" not in stdout:
            passed = stdout.count(": PASS")

        # ── Step 4: Score Calculation ──────────────────────────────────────────
        compile_bonus = 0.20
        vector_score  = (passed / total) * 0.70
        score = round(compile_bonus + vector_score, 2)

        logs.append(f"\n📋 STEP 4: Score Breakdown:")
        logs.append(f"  ✅ Compilation bonus:  +0.20")
        logs.append(f"  📈 Vector score:       +{vector_score:.2f}  ({passed}/{total} × 0.70)")
        logs.append(f"  ─────────────────────────────")
        logs.append(f"  🏆 FINAL SCORE:        {score:.2f} / 0.90 max")

        status = "success" if passed == total else "logic_error"
        return {
            "status": status,
            "compile_error": "",
            "sim_output": stdout,
            "passed": passed,
            "total": total,
            "score": score,
            "logs": "\n".join(logs),
            "vector_results": vector_results
        }


@app.post("/grade/{task_id}")
async def grade_task(task_id: str, body: dict = Body(...)):
    """
    POST endpoint — accepts any Verilog code and grades it dynamically.
    Body: { "verilog_code": "..." }
    """
    if task_id not in TOTALS:
        return {"status": "error", "score": 0.0, "logs": f"Unknown task: {task_id}"}
    verilog = body.get("verilog_code", "")
    if not verilog.strip():
        return {"status": "error", "score": 0.0, "logs": "Empty Verilog code submitted."}
    return _grade_verilog(task_id, verilog)


@app.post("/ai-fix/{task_id}")
async def ai_fix_task(task_id: str, body: dict = Body(...)):
    """
    POST endpoint — sends broken Verilog + error context to LLM for auto-repair.
    Body: { "verilog_code": "...", "error_log": "...", "task_spec": "..." }
    Returns: { "fixed_code": "...", "explanation": "..." }
    """
    from openai import OpenAI

    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("HF_TOKEN")
    if not api_key:
        return {
            "status": "error",
            "fixed_code": "",
            "explanation": "⚠️ No API key found. Set OPENAI_API_KEY or HF_TOKEN in Space secrets to enable AI auto-fix."
        }

    api_base = os.getenv("API_BASE_URL", "https://api.openai.com/v1")
    model    = os.getenv("MODEL_NAME", "gpt-4o-mini")

    broken_code = body.get("verilog_code", "")
    error_log   = body.get("error_log", "None")
    task_spec   = body.get("task_spec", "Fix the Verilog module so it compiles and passes all simulation tests.")

    prompt = f"""You are an expert RTL hardware engineer. Fix the broken Verilog module below.

TASK SPECIFICATION:
{task_spec}

BROKEN VERILOG:
{broken_code}

SIMULATION/COMPILE ERRORS:
{error_log}

INSTRUCTIONS:
- Return ONLY the complete corrected Verilog module
- Do NOT add markdown fences (no ```verilog)
- Do NOT add any explanation outside the code
- Keep all module names, port names, and parameters unchanged
- Fix ONLY what is broken — preserve correct logic"""

    try:
        client = OpenAI(base_url=api_base, api_key=api_key)
        completion = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=1500,
        )
        fixed = (completion.choices[0].message.content or "").strip()
        # Strip markdown fences if model added them anyway
        import re as _re
        fixed = _re.sub(r"```(?:verilog|systemverilog|sv)?\s*", "", fixed)
        fixed = _re.sub(r"```\s*$", "", fixed, flags=_re.MULTILINE).strip()

        return {"status": "ok", "fixed_code": fixed, "explanation": f"Fixed by {model}"}
    except Exception as e:
        return {"status": "error", "fixed_code": broken_code, "explanation": f"AI call failed: {str(e)}"}


@app.get("/verify/{task_id}")
async def verify_task(task_id: str, mode: str = "broken"):
    """GET endpoint — grades the preset broken.v or correct.v file."""
    if task_id not in TOTALS:
        return {"status": "error", "score": 0.0}
    base_dir = f"server/tasks/{task_id}"
    v_file = "broken.v" if mode == "broken" else "correct.v"
    try:
        with open(f"{base_dir}/{v_file}") as f:
            code = f.read()
        return _grade_verilog(task_id, code)
    except FileNotFoundError:
        return {"status": "error", "score": 0.0, "logs": f"{v_file} not found for task {task_id}"}


def _load_task_code(task_id: str, filename: str) -> str:
    try:
        with open(f"server/tasks/{task_id}/{filename}") as f:
            return f.read().replace("`", "&#96;").replace("</", "<\\/")
    except:
        return f"// {filename} not found"


@app.get("/", response_class=HTMLResponse)
def read_root():
    easy_broken   = _load_task_code("easy",   "broken.v")
    medium_broken = _load_task_code("medium", "broken.v")
    hard_broken   = _load_task_code("hard",   "broken.v")
    easy_correct  = _load_task_code("easy",   "correct.v")
    medium_correct= _load_task_code("medium", "correct.v")
    hard_correct  = _load_task_code("hard",   "correct.v")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>RTLRepair | Live Hardware Debugger</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
    <style>
        :root {{
            --p:#6366f1; --bg:#0b0f1a; --c:#161b2c; --c2:#1e2537;
            --t:#f8fafc; --acc:#38bdf8; --g:#4ade80; --r:#fb7185; --y:#fbbf24;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ background:var(--bg); color:var(--t); font-family:'Inter',sans-serif; padding:2rem; }}

        .hero {{ text-align:center; margin-bottom:3rem; }}
        .hero h1 {{ font-size:2.8rem; font-weight:800; color:var(--acc); }}
        .hero p {{ opacity:.6; margin-top:.5rem; }}
        .badge {{ display:inline-block; margin-top:1rem; font-size:.75rem;
                  background:rgba(99,102,241,.15); padding:.3rem 1rem;
                  border-radius:9999px; border:1px solid var(--p); }}

        .task-panel {{ background:var(--c); border:1px solid rgba(255,255,255,.08);
                       border-radius:1.5rem; padding:2rem; margin-bottom:2.5rem; }}
        .task-header {{ display:flex; justify-content:space-between; align-items:flex-start;
                        margin-bottom:1.5rem; gap:1rem; flex-wrap:wrap; }}
        .task-title h2 {{ font-size:1.3rem; font-weight:700; }}
        .task-title p {{ opacity:.5; font-size:.85rem; margin-top:.2rem; }}

        .btn-group {{ display:flex; gap:.5rem; flex-wrap:wrap; }}
        .btn {{ padding:.5rem 1.1rem; border-radius:.7rem; font-weight:700;
                font-size:.82rem; cursor:pointer; border:none; transition:.15s; }}
        .btn:hover {{ transform:scale(1.04); filter:brightness(1.1); }}
        .btn-broken {{ background:rgba(255,255,255,.1); color:var(--t);
                       border:1px solid rgba(255,255,255,.2); }}
        .btn-fixed  {{ background:var(--p); color:#fff; }}
        .btn-run    {{ background:var(--acc); color:#000; }}

        .editor-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:1rem;
                        margin-bottom:1rem; }}
        .editor-box {{ display:flex; flex-direction:column; gap:.4rem; }}
        .editor-box label {{ font-size:.7rem; font-weight:700; opacity:.5;
                             text-transform:uppercase; letter-spacing:.05em; }}
        textarea.verilog-editor {{
            background:#000; color:#e2e8f0; border:1px solid rgba(255,255,255,.1);
            border-radius:.8rem; padding:1rem; font-family:'JetBrains Mono',monospace;
            font-size:.78rem; resize:vertical; min-height:180px; outline:none;
            transition:border .2s;
        }}
        textarea.verilog-editor:focus {{ border-color:var(--p); }}

        .log-panel {{ background:#05070a; border:1px solid #1e2537; border-radius:1rem;
                      padding:1.2rem; margin-top:1rem; display:none; }}
        .log-header {{ display:flex; justify-content:space-between; align-items:center;
                       font-size:.7rem; font-weight:700; opacity:.4;
                       text-transform:uppercase; margin-bottom:.8rem; }}
        .log-scroll {{ max-height:320px; overflow-y:auto; padding-right:.4rem; }}
        .log-scroll::-webkit-scrollbar {{ width:4px; }}
        .log-scroll::-webkit-scrollbar-track {{ background:transparent; }}
        .log-scroll::-webkit-scrollbar-thumb {{ background:var(--p); border-radius:2px; }}
        .log-body {{ font-family:'JetBrains Mono',monospace; font-size:.78rem;
                     white-space:pre-wrap; line-height:1.7; }}
        .fix-tip {{ margin-top:.8rem; padding:.6rem 1rem; background:rgba(251,191,36,.1);
                    border:1px solid var(--y); border-radius:.6rem; font-size:.78rem;
                    color:var(--y); display:none; }}
        .score-badge {{ display:inline-block; font-family:'JetBrains Mono'; font-weight:700;
                        padding:.25rem .75rem; border-radius:.4rem; font-size:.9rem;
                        margin-bottom:.5rem; }}
        .score-pass {{ background:var(--g); color:#000; }}
        .score-fail {{ background:var(--r); color:#fff; }}
        .score-warn {{ background:var(--y); color:#000; }}
        .btn-ai {{ background:linear-gradient(135deg,#7c3aed,#6366f1); color:#fff; }}
        .btn-ai:disabled {{ opacity:.5; cursor:not-allowed; }}

        @media(max-width:700px) {{
            .editor-grid {{ grid-template-columns:1fr; }}
            .task-header {{ flex-direction:column; }}
        }}
    </style>
</head>
<body>
    <div class="hero">
        <h1>🛠️ RTLRepair Platform</h1>
        <p>Interactive Hardware Bug Diagnosis & Live Simulation Benchmark</p>
        <div class="badge">📡 <b>LIVE:</b> Edit any module and click Run to grade in real-time</div>
    </div>

    <!-- ─── EASY ─── -->
    <div class="task-panel">
        <div class="task-header">
            <div class="task-title">
                <h2>Level 01: 4-bit Synchronous Counter</h2>
                <p>Syntax &amp; Port Sensitivities — 5 test vectors</p>
            </div>
            <div class="btn-group">
                <button class="btn btn-broken" onclick="loadPreset('easy','broken')">Load Broken</button>
                <button class="btn btn-fixed"  onclick="loadPreset('easy','fixed')">Load Solution</button>
                <button class="btn btn-run"    onclick="runGrade('easy')">&#9654; Run &amp; Grade</button>
                <button class="btn btn-ai" id="ai-btn-easy" onclick="autoFix('easy')">&#129302; Auto-Fix</button>
            </div>
        </div>
        <div class="editor-grid">
            <div class="editor-box">
                <label>✏️ Your Verilog (editable)</label>
                <textarea class="verilog-editor" id="code-easy">{easy_broken}</textarea>
            </div>
            <div class="editor-box">
                <label>📖 Repair Reference (read-only)</label>
                <textarea class="verilog-editor" id="ref-easy" readonly style="opacity:.55">{easy_correct}</textarea>
            </div>
        </div>
        <div class="log-panel" id="log-easy">
            <div class="log-header">
                <span>Simulation Log</span>
                <span style="opacity:.5;font-weight:400">Scroll to see all output ↕</span>
            </div>
            <div class="log-scroll">
                <div class="log-body" id="log-body-easy"></div>
            </div>
            <div class="fix-tip" id="fix-tip-easy">
                &#128161; <b>Errors detected!</b> Edit the code above and re-run, or click
                <b>&#129302; Auto-Fix</b> to let the AI repair it automatically.
            </div>
        </div>
    </div>

    <!-- ─── MEDIUM ─── -->
    <div class="task-panel">
        <div class="task-header">
            <div class="task-title">
                <h2>Level 02: 4-bit ALU Unit</h2>
                <p>Behavioral Arithmetic Logic — 10 test vectors</p>
            </div>
            <div class="btn-group">
                <button class="btn btn-broken" onclick="loadPreset('medium','broken')">Load Broken</button>
                <button class="btn btn-fixed"  onclick="loadPreset('medium','fixed')">Load Solution</button>
                <button class="btn btn-run"    onclick="runGrade('medium')">&#9654; Run &amp; Grade</button>
                <button class="btn btn-ai" id="ai-btn-medium" onclick="autoFix('medium')">&#129302; Auto-Fix</button>
            </div>
        </div>
        <div class="editor-grid">
            <div class="editor-box">
                <label>✏️ Your Verilog (editable)</label>
                <textarea class="verilog-editor" id="code-medium">{medium_broken}</textarea>
            </div>
            <div class="editor-box">
                <label>📖 Repair Reference (read-only)</label>
                <textarea class="verilog-editor" id="ref-medium" readonly style="opacity:.55">{medium_correct}</textarea>
            </div>
        </div>
        <div class="log-panel" id="log-medium">
            <div class="log-header">
                <span>Simulation Log</span>
                <span style="opacity:.5;font-weight:400">Scroll to see all output ↕</span>
            </div>
            <div class="log-scroll">
                <div class="log-body" id="log-body-medium"></div>
            </div>
            <div class="fix-tip" id="fix-tip-medium">
                &#128161; <b>Errors detected!</b> Edit the code above and re-run, or click
                <b>&#129302; Auto-Fix</b> to let the AI repair it automatically.
            </div>
        </div>
    </div>

    <!-- ─── HARD ─── -->
    <div class="task-panel">
        <div class="task-header">
            <div class="task-title">
                <h2>Level 03: Traffic Light FSM</h2>
                <p>Finite State Machine Transitions — 20 test vectors</p>
            </div>
            <div class="btn-group">
                <button class="btn btn-broken" onclick="loadPreset('hard','broken')">Load Broken</button>
                <button class="btn btn-fixed"  onclick="loadPreset('hard','fixed')">Load Solution</button>
                <button class="btn btn-run"    onclick="runGrade('hard')">&#9654; Run &amp; Grade</button>
                <button class="btn btn-ai" id="ai-btn-hard" onclick="autoFix('hard')">&#129302; Auto-Fix</button>
            </div>
        </div>
        <div class="editor-grid">
            <div class="editor-box">
                <label>✏️ Your Verilog (editable)</label>
                <textarea class="verilog-editor" id="code-hard">{hard_broken}</textarea>
            </div>
            <div class="editor-box">
                <label>📖 Repair Reference (read-only)</label>
                <textarea class="verilog-editor" id="ref-hard" readonly style="opacity:.55">{hard_correct}</textarea>
            </div>
        </div>
        <div class="log-panel" id="log-hard">
            <div class="log-header">
                <span>Simulation Log</span>
                <span style="opacity:.5;font-weight:400">Scroll to see all output ↕</span>
            </div>
            <div class="log-scroll">
                <div class="log-body" id="log-body-hard"></div>
            </div>
            <div class="fix-tip" id="fix-tip-hard">
                &#128161; <b>Errors detected!</b> Edit the code above and re-run, or click
                <b>&#129302; Auto-Fix</b> to let the AI repair it automatically.
            </div>
        </div>
    </div>

<script>
const PRESETS = {{
    easy:   {{ broken: {repr(easy_broken)},   fixed: {repr(easy_correct)} }},
    medium: {{ broken: {repr(medium_broken)}, fixed: {repr(medium_correct)} }},
    hard:   {{ broken: {repr(hard_broken)},   fixed: {repr(hard_correct)} }}
}};

const TASK_SPECS = {{
    easy:   "4-bit synchronous up-counter. Fix port direction (output reg), clock edge (posedge), and undeclared signal.",
    medium: "4-bit ALU with ops ADD/SUB/AND/OR. Fix wrong operators in SUB and AND cases.",
    hard:   "3-state traffic light FSM: RED->GREEN->YELLOW->RED. Fix state transitions and timer thresholds."
}};

const lastLog = {{}};

function loadPreset(tid, mode) {{
    document.getElementById(`code-${{tid}}`).value = PRESETS[tid][mode];
}}

async function runGrade(tid) {{
    const code = document.getElementById(`code-${{tid}}`).value;
    const logPanel = document.getElementById(`log-${{tid}}`);
    const logBody  = document.getElementById(`log-body-${{tid}}`);
    const fixTip   = document.getElementById(`fix-tip-${{tid}}`);

    logPanel.style.display = "block";
    fixTip.style.display   = "none";
    logBody.innerHTML = "<span style='color:var(--acc)'>&#9889; Compiling and simulating...</span>";

    try {{
        const res = await fetch(`/grade/${{tid}}`, {{
            method: "POST",
            headers: {{ "Content-Type": "application/json" }},
            body: JSON.stringify({{ verilog_code: code }})
        }});
        const data = await res.json();

        const score   = data.score ?? 0;
        const total   = data.total ?? "?";
        const passed  = data.passed ?? 0;
        const isError = data.status === "compile_error" || data.status === "logic_error";
        const scoreClass = score >= 0.85 ? "score-pass" : score >= 0.35 ? "score-warn" : "score-fail";

        const scoreLine = `<div class="score-badge ${{scoreClass}}">SCORE: ${{score.toFixed(2)}} &nbsp;|&nbsp; ${{passed}}/${{total}} vectors passed</div>`;
        const logText   = (data.logs || "No output").replace(/</g,"&lt;").replace(/>/g,"&gt;");

        lastLog[tid] = data.logs || "";
        logBody.innerHTML = scoreLine + "\n\n" + logText;

        if (isError) fixTip.style.display = "block";
        else fixTip.style.display = "none";

        logPanel.querySelector(".log-scroll").scrollTop = 0;

    }} catch(e) {{
        logBody.innerHTML = `<span style='color:var(--r)'>&#10060; Request failed: ${{e.message}}</span>`;
        fixTip.style.display = "block";
    }}
}}

async function autoFix(tid) {{
    const code    = document.getElementById(`code-${{tid}}`).value;
    const logBody = document.getElementById(`log-body-${{tid}}`);
    const logPanel= document.getElementById(`log-${{tid}}`);
    const fixTip  = document.getElementById(`fix-tip-${{tid}}`);
    const btn     = document.getElementById(`ai-btn-${{tid}}`);

    logPanel.style.display = "block";
    fixTip.style.display   = "none";
    btn.disabled = true;
    btn.textContent = "&#129302; Thinking...";
    logBody.innerHTML = "<span style='color:#a78bfa'>&#129302; Sending to AI for analysis and repair...</span>";

    try {{
        const res = await fetch(`/ai-fix/${{tid}}`, {{
            method: "POST",
            headers: {{ "Content-Type": "application/json" }},
            body: JSON.stringify({{
                verilog_code: code,
                error_log: lastLog[tid] || "No previous run. Inspect the code for common Verilog bugs.",
                task_spec: TASK_SPECS[tid]
            }})
        }});
        const data = await res.json();

        if (data.status === "ok" && data.fixed_code) {{
            document.getElementById(`code-${{tid}}`).value = data.fixed_code;
            logBody.innerHTML = `<span style='color:#a78bfa'>&#129302; ${{data.explanation}}</span>\n<span style='color:var(--g)'>&#10003; Code updated — running grader now...</span>`;
            // Auto-run grader with fixed code
            setTimeout(() => runGrade(tid), 600);
        }} else {{
            logBody.innerHTML = `<span style='color:var(--r)'>&#10060; AI fix failed: ${{data.explanation}}</span>`;
            fixTip.style.display = "block";
        }}
    }} catch(e) {{
        logBody.innerHTML = `<span style='color:var(--r)'>&#10060; AI request failed: ${{e.message}}</span>`;
        fixTip.style.display = "block";
    }} finally {{
        btn.disabled = false;
        btn.textContent = "&#129302; Auto-Fix";
    }}
}}
</script>
</body>
</html>"""