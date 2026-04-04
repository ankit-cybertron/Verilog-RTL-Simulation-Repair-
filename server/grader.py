"""
grader.py — RTLRepair-Env deterministic grading logic

All scoring is pure Python + iverilog subprocess.
No LLM graders. Same input always produces same score.
"""

import os
import subprocess
import tempfile
import re
from typing import Tuple, List, Dict

# Task configuration
TASK_CONFIG = {
    "easy": {
        "max_steps": 3,
        "vectors_total": 5,
        "broken_file": "tasks/easy/broken.v",
        "testbench_file": "tasks/easy/testbench.v",
        "golden_file": "tasks/easy/golden.txt",
        "module_name": "counter_4bit",
        "module_spec": (
            "4-bit synchronous up-counter with enable and active-high synchronous reset. "
            "Increments count on every rising clock edge when enable=1. "
            "When reset=1, count is synchronously cleared to 0 on the next rising edge. "
            "Output 'count' is a 4-bit register reflecting the current counter value."
        ),
    },
    "medium": {
        "max_steps": 5,
        "vectors_total": 10,
        "broken_file": "tasks/medium/broken.v",
        "testbench_file": "tasks/medium/testbench.v",
        "golden_file": "tasks/medium/golden.txt",
        "module_name": "alu_4bit",
        "module_spec": (
            "4-bit ALU with 4 operations selected by 2-bit 'op': "
            "op=00 ADD (result=a+b), op=01 SUB (result=a-b), "
            "op=10 AND (result=a&b), op=11 OR (result=a|b). "
            "Output 'zero' is high when result==0. All operations are combinatorial."
        ),
    },
    "hard": {
        "max_steps": 7,
        "vectors_total": 20,
        "broken_file": "tasks/hard/broken.v",
        "testbench_file": "tasks/hard/testbench.v",
        "golden_file": "tasks/hard/golden.txt",
        "module_name": "traffic_light",
        "module_spec": (
            "3-state traffic light FSM: RED (3 cycles) → GREEN (3 cycles) → YELLOW (1 cycle) → RED. "
            "Outputs: red_light=1 in RED state, green_light=1 in GREEN state, yellow_light=1 in YELLOW state. "
            "All outputs are registered (updated on posedge clk). "
            "Synchronous active-high reset returns to RED state with timer cleared to 0. "
            "State transitions are driven by an internal timer that counts cycles per state."
        ),
    },
}

# Directory of this file — used to locate task files
SERVER_DIR = os.path.dirname(os.path.abspath(__file__))

IVERILOG_TIMEOUT = 10  # seconds — never let grader hang


def _task_path(task_id: str, filename: str) -> str:
    return os.path.join(SERVER_DIR, TASK_CONFIG[task_id][filename])


def _load_golden(task_id: str) -> List[str]:
    with open(_task_path(task_id, "golden_file")) as f:
        return [line.strip() for line in f if line.strip()]


def compile_verilog(
    agent_verilog: str,
    task_id: str,
    tmp_dir: str,
) -> Tuple[bool, str, str]:
    """
    Write agent_verilog to a temp file, compile with iverilog against
    the task testbench. Returns (success, error_output, sim_binary_path).
    """
    # Write agent code to temp file
    agent_file = os.path.join(tmp_dir, "agent_module.v")
    with open(agent_file, "w") as f:
        f.write(agent_verilog)

    tb_file = _task_path(task_id, "testbench_file")
    sim_bin = os.path.join(tmp_dir, "sim")

    try:
        result = subprocess.run(
            ["iverilog", "-o", sim_bin, agent_file, tb_file],
            capture_output=True,
            text=True,
            timeout=IVERILOG_TIMEOUT,
        )
        if result.returncode == 0:
            return True, "", sim_bin
        else:
            error_msg = result.stderr or result.stdout or "Unknown compile error"
            return False, error_msg.strip(), ""
    except subprocess.TimeoutExpired:
        return False, "Compilation timed out (>10s)", ""
    except FileNotFoundError:
        return False, "iverilog not found — check Dockerfile", ""
    except Exception as e:
        return False, f"Compilation error: {str(e)}", ""


def run_simulation(sim_bin: str) -> Tuple[bool, str]:
    """
    Run the compiled simulation binary.
    Returns (success, stdout_output).
    """
    try:
        result = subprocess.run(
            [sim_bin],
            capture_output=True,
            text=True,
            timeout=IVERILOG_TIMEOUT,
        )
        return True, result.stdout.strip()
    except subprocess.TimeoutExpired:
        return False, "Simulation timed out (>10s)"
    except Exception as e:
        return False, f"Simulation error: {str(e)}"


def score_simulation_output(
    sim_output: str,
    task_id: str,
) -> Tuple[int, int, List[Dict]]:
    """
    Compare simulation output line-by-line against golden output.
    Returns (passed_count, total_count, per_vector_results).
    """
    golden_lines = _load_golden(task_id)
    sim_lines = [line.strip() for line in sim_output.split("\n") if line.strip()]
    total = len(golden_lines)
    passed = 0
    results = []

    for i, expected in enumerate(golden_lines):
        actual = sim_lines[i] if i < len(sim_lines) else "<missing>"
        ok = actual == expected
        if ok:
            passed += 1
        results.append({
            "vector_id": i + 1,
            "passed": ok,
            "expected": expected,
            "actual": actual,
        })

    return passed, total, results


def count_compile_errors(error_output: str) -> int:
    """Count number of distinct error lines from iverilog output."""
    return len([
        line for line in error_output.split("\n")
        if "error" in line.lower() and line.strip()
    ])


def compute_reward(
    agent_verilog: str,
    task_id: str,
    prev_error_count: int = 999,
    current_step: int = 1,
) -> Tuple[float, str, str, int, int, List[Dict]]:
    """
    Main grading function. Deterministic — same input always gives same score.

    Reward breakdown:
      +0.20  compilation succeeds
      +0.05  per error eliminated vs previous step (partial credit)
      +0.70  fraction of test vectors passing (0.70 * passed/total)
      +0.10  surgical precision bonus (didn't break correct lines)
      -0.02  per step taken (encourages fewer steps)

    Returns:
      (reward, compile_error, sim_output, vectors_passed, vectors_total, vector_results)
    """
    # Guard: empty or non-string input
    if not agent_verilog or not isinstance(agent_verilog, str):
        return 0.0, "Empty or invalid Verilog submitted", "", 0, 0, []

    # Strip markdown fences if agent wrapped code in ```verilog ... ```
    cleaned = re.sub(r"```(?:verilog|systemverilog|sv)?\s*", "", agent_verilog)
    cleaned = re.sub(r"```\s*$", "", cleaned, flags=re.MULTILINE).strip()

    reward = 0.0
    compile_error = ""
    sim_output = ""
    vectors_passed = 0
    vectors_total = TASK_CONFIG[task_id]["vectors_total"]
    vector_results = []

    with tempfile.TemporaryDirectory() as tmp_dir:
        # --- Tier 1: Compilation ---
        compile_ok, compile_error, sim_bin = compile_verilog(cleaned, task_id, tmp_dir)

        if compile_ok:
            reward += 0.20
        else:
            # Partial credit: reward for reducing error count vs previous step
            new_error_count = count_compile_errors(compile_error)
            errors_fixed = max(0, prev_error_count - new_error_count)
            reward += min(0.15, 0.05 * errors_fixed)
            # Return early — can't simulate if compile failed
            reward -= 0.02 * current_step
            return (
                max(0.0, min(1.0, reward)),
                compile_error, sim_output,
                vectors_passed, vectors_total, vector_results,
            )

        # --- Tier 2: Simulation ---
        sim_ok, sim_output = run_simulation(sim_bin)

        if sim_ok and sim_output:
            vectors_passed, vectors_total, vector_results = score_simulation_output(
                sim_output, task_id
            )
            reward += 0.70 * (vectors_passed / vectors_total)

        # --- Tier 3: Surgical precision bonus ---
        # Reward agent for not touching lines that were already correct
        # Compare unchanged lines vs broken.v baseline
        try:
            with open(_task_path(task_id, "broken_file")) as f:
                original_lines = set(f.read().splitlines())
            agent_lines = set(cleaned.splitlines())
            # Lines the agent kept from the original (some were correct)
            kept = original_lines & agent_lines
            # Rough heuristic: if agent kept >70% of original lines, +0.10
            if len(original_lines) > 0 and len(kept) / len(original_lines) > 0.70:
                reward += 0.10
        except Exception:
            pass  # Don't crash grader on file read issues

    # Step cost penalty
    reward -= 0.02 * current_step

    return (
        max(0.0, min(1.0, reward)),
        compile_error,
        sim_output,
        vectors_passed,
        vectors_total,
        vector_results,
    )


def get_task_config(task_id: str) -> dict:
    """Return config dict for a given task_id."""
    if task_id not in TASK_CONFIG:
        raise ValueError(f"Unknown task_id: {task_id!r}. Must be one of {list(TASK_CONFIG)}")
    return TASK_CONFIG[task_id]


def load_broken_module(task_id: str) -> str:
    """Load the broken Verilog module for a task."""
    with open(_task_path(task_id, "broken_file")) as f:
        return f.read()