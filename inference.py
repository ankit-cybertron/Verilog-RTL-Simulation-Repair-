"""
inference.py — RTLRepair-Env baseline inference script

MANDATORY: This file must be in the ROOT directory of the project.
Uses the OpenAI client (required by hackathon rules).
Reads credentials from environment variables.
Emits [START], [STEP], [END] structured logs to stdout.

Usage:
    export API_BASE_URL="https://api.openai.com/v1"
    export MODEL_NAME="gpt-4o-mini"
    export HF_TOKEN="your-key-here"
    export HF_SPACE_URL="https://your-username-rtlrepair-env.hf.space"
    python inference.py
"""

import os
import json
import asyncio
from typing import List
from openai import OpenAI
from client import RTLRepairEnv, RTLAction

# ── Environment variables (crash loudly if missing) ──────────────────────────
API_BASE_URL = os.environ.get("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME   = os.environ.get("MODEL_NAME", "gpt-4o-mini")
HF_TOKEN     = os.environ["HF_TOKEN"]          # Required — crashes if unset
HF_SPACE_URL = os.environ.get(
    "HF_SPACE_URL", "http://localhost:7860"
)

# ── Episode config ────────────────────────────────────────────────────────────
TASKS = ["easy", "medium", "hard"]
MAX_STEPS = {"easy": 3, "medium": 5, "hard": 7}
MAX_TOTAL_REWARD = 1.0
SUCCESS_SCORE_THRESHOLD = 0.7
TEMPERATURE = 0.1      # Low temp for reproducibility
MAX_TOKENS  = 1500

# ── Structured logging (judges parse this programmatically) ──────────────────
def log_start(task: str, env: str, model: str) -> None:
    print(json.dumps({
        "type": "START",
        "task": task,
        "env": env,
        "model": model,
    }), flush=True)

def log_step(step: int, action: str, reward: float, done: bool, error) -> None:
    print(json.dumps({
        "type": "STEP",
        "step": step,
        "action": action[:120],   # truncate for readability
        "reward": round(reward, 4),
        "done": done,
        "error": error,
    }), flush=True)

def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    print(json.dumps({
        "type": "END",
        "success": success,
        "steps": steps,
        "score": round(score, 4),
        "rewards": [round(r, 4) for r in rewards],
    }), flush=True)

# ── System prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are an expert RTL hardware engineer specializing in Verilog debugging.

Your task: Receive a broken Verilog module and return a corrected version.

Rules:
1. Return ONLY the complete, corrected Verilog module — no explanation text outside the code
2. Do NOT wrap your response in markdown fences (no ```verilog or ```)
3. Keep all module ports, parameters, and names exactly as given in the spec
4. Fix ONLY what is wrong — do not restructure correct parts unnecessarily
5. Use the compile_error and sim_output feedback to guide your fix

Common Verilog bugs to look for:
- Wrong signal names (undeclared variables)
- Missing or extra signals in always block sensitivity lists
- Wrong operators (& vs |, + vs -, == vs !=)
- Incorrect reset polarity or timing (sync vs async)
- Wrong state machine transitions or output assignments
- Combinatorial vs registered output mismatches"""

# ── Model interaction ─────────────────────────────────────────────────────────
def get_model_response(
    client: OpenAI,
    observation,
    history: List[str],
    step: int,
) -> str:
    """Call the LLM and get a repaired Verilog module."""
    user_prompt = f"""Fix the broken Verilog module below.

MODULE SPECIFICATION (what it should do):
{observation.broken_module and observation.module_spec}

BROKEN MODULE (contains bugs — do not trust this):
{observation.broken_module}

COMPILE ERROR FROM LAST ATTEMPT:
{observation.compile_error or "None — module compiled successfully"}

SIMULATION OUTPUT FROM LAST ATTEMPT:
{observation.sim_output or "Not run — compilation failed"}

TEST VECTORS: {observation.vectors_passed}/{observation.vectors_total} passing

STEP HISTORY:
{chr(10).join(history[-3:]) if history else "First attempt"}

Return the complete corrected Verilog module (no markdown, no explanation):"""

    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_prompt},
            ],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            stream=False,
        )
        text = (completion.choices[0].message.content or "").strip()
        return text if text else "// empty response fallback\nmodule fallback(); endmodule"
    except Exception as exc:
        print(f"[DEBUG] Model request failed: {exc}", flush=True)
        return "// model error fallback\nmodule fallback(); endmodule"


# ── Episode runner ────────────────────────────────────────────────────────────
async def run_task(task_id: str) -> float:
    """Run one full episode for a given task. Returns final score."""
    client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)

    log_start(task=task_id, env="RTLRepair-Env", model=MODEL_NAME)

    history: List[str] = []
    rewards: List[float] = []
    steps_taken = 0
    score = 0.0
    success = False

    async with RTLRepairEnv(base_url=HF_SPACE_URL) as env:
        # Reset environment
        result = await env.reset(task_id=task_id)
        obs = result.observation

        for step in range(1, MAX_STEPS[task_id] + 1):
            if result.done:
                break

            # Get model response
            verilog = get_model_response(client, obs, history, step)

            # Step environment
            result = await env.step(RTLAction(
                verilog_code=verilog,
                explanation=f"Step {step} attempt",
            ))
            obs = result.observation
            reward = result.reward or 0.0
            done = result.done

            rewards.append(reward)
            steps_taken = step

            log_step(
                step=step,
                action=verilog[:120],
                reward=reward,
                done=done,
                error=obs.compile_error[:80] if obs.compile_error else None,
            )

            history.append(
                f"Step {step}: {obs.vectors_passed}/{obs.vectors_total} vectors passed, "
                f"reward={reward:.3f}, compile_error={bool(obs.compile_error)}"
            )

            if done:
                break

        # Final score: best reward achieved across all steps (not average)
        score = max(rewards) if rewards else 0.0
        score = min(max(score, 0.0), 1.0)
        success = score >= SUCCESS_SCORE_THRESHOLD

    log_end(success=success, steps=steps_taken, score=score, rewards=rewards)
    return score


# ── Main ──────────────────────────────────────────────────────────────────────
async def main() -> None:
    print(f"[INFO] RTLRepair-Env baseline inference", flush=True)
    print(f"[INFO] Model: {MODEL_NAME}", flush=True)
    print(f"[INFO] Space: {HF_SPACE_URL}", flush=True)

    scores = {}
    for task_id in TASKS:
        print(f"\n[INFO] Running task: {task_id}", flush=True)
        scores[task_id] = await run_task(task_id)

    print(f"\n[RESULTS] {json.dumps({'final_scores': scores})}", flush=True)
    avg = sum(scores.values()) / len(scores)
    print(f"[RESULTS] Average score: {avg:.4f}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())