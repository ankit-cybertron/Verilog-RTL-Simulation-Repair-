---
title: RTLRepair-Env
emoji: 🛠️
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
license: mit
---

# RTLRepair-Env

**The first Verilog RTL debugging environment in the OpenEnv ecosystem.**

## Motivation

A single RTL bug that reaches chip tapeout costs **$5–50 million** to fix.
Cadence, Synopsys, and Intel are actively building LLM-based RTL debugging
assistants — yet no open benchmark exists to evaluate them.

RTLRepair-Env fills that gap: an AI agent receives a broken Verilog hardware
module and must repair it to pass iverilog simulation tests. Built on the
OpenEnv framework for reproducible, deterministic evaluation.

## Environment Overview

| Property | Value |
|---|---|
| Action space | `RTLAction` — repaired Verilog module (string) |
| Observation space | `RTLObservation` — broken module, spec, compile errors, sim output |
| Grader | `iverilog` — deterministic, no LLM grader |
| Compute | ~50MB (iverilog only) |
| Max runtime | < 5 min for all 3 tasks |

## Action Space

| Field | Type | Description |
|---|---|---|
| `verilog_code` | `str` | Complete repaired Verilog module |
| `explanation` | `str` | Optional reasoning (not graded) |

## Observation Space

| Field | Type | Description |
|---|---|---|
| `task_id` | `str` | `"easy"` / `"medium"` / `"hard"` |
| `module_name` | `str` | Name of the module to repair |
| `module_spec` | `str` | Natural language description of intended behavior |
| `broken_module` | `str` | The broken Verilog code to fix |
| `compile_error` | `str` | iverilog output (empty = compiled OK) |
| `sim_output` | `str` | Simulation stdout (empty if compile failed) |
| `test_vector_results` | `list[dict]` | Per-vector pass/fail |
| `vectors_passed` | `int` | Test vectors passing |
| `vectors_total` | `int` | Total test vectors |
| `reward` | `float` | Step reward 0.0–1.0 |
| `done` | `bool` | Episode complete |

## Tasks

### Easy — Compile repair (3 steps max)
4-bit synchronous counter with 3 injected bugs: wrong signal name,
incorrect always block sensitivity list, wrong reset signal name.
The module fails to compile. Agent must fix it to compile and pass 5 test vectors.
**Expected baseline score: ~0.65**

### Medium — Logic repair (5 steps max)
4-bit ALU with 2 semantic bugs: wrong operator in subtraction path,
wrong operator in AND operation. The module compiles but produces wrong output.
Agent must fix logic to pass 10 test vectors.
**Expected baseline score: ~0.45**

### Hard — FSM repair (7 steps max)
3-state traffic light FSM with 3 bugs: wrong state timer threshold,
missing GREEN→YELLOW transition, unregistered yellow_light output.
Agent must fix all 3 bugs to pass 20 test vectors covering all state paths.
**Expected baseline score: ~0.20**

## Reward Function

| Component | Value |
|---|---|
| Compilation succeeds | +0.20 |
| Each error eliminated (vs prev step) | +0.05 |
| Fraction of test vectors passing | +0.70 × (passed/total) |
| Surgical precision (kept correct lines) | +0.10 |
| Step cost | −0.02 × step_number |

## Setup

```bash
# Install
pip install "openenv-core[core]>=0.2.1"

# Run locally
uvicorn server.app:app --host 0.0.0.0 --port 7860

# Docker
docker build -t rtlrepair-env .
docker run -p 7860:7860 rtlrepair-env

# Run baseline
export API_BASE_URL="https://api.openai.com/v1"
export MODEL_NAME="gpt-4o-mini"
export HF_TOKEN="your-key"
export HF_SPACE_URL="https://your-username-rtlrepair-env.hf.space"
python inference.py
```

## Baseline Scores

Model: `gpt-4o-mini` | Temperature: 0.1

| Task | Score |
|---|---|
| Easy | 0.65 |
| Medium | 0.42 |
| Hard | 0.21 |
| **Average** | **0.43** |

## Roadmap (Phase 2)

- Synthesis repair (Yosys integration)
- Timing constraint debugging
- Multi-module hierarchy repair
- SystemVerilog support
