---
title: Rtlrepair Env
emoji: 🛠️
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
---

# 🛠️ Verilog RTL Simulation Repair Environment

**Automated hardware debugging at scale using AI agents.**

[![OpenEnv](https://img.shields.io/badge/Framework-OpenEnv-brightgreen)](https://github.com/meta-pytorch/openenv-core)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Hugging Face](https://img.shields.io/badge/%F0%9F%A4%97%20Space-Running-blue)](https://huggingface.co/spaces/cybertronak/rtlrepair-env)

RTLRepair-Env is a specialized **AI agent benchmark environment** for hardware engineering. It challenges LLMs to find and fix bugs in Verilog source code, mirroring the high-stakes world of semiconductor design.

- **🚀 Live Space:** [https://huggingface.co/spaces/cybertronak/rtlrepair-env](https://huggingface.co/spaces/cybertronak/rtlrepair-env)
- **💻 GitHub Code:** [https://github.com/ankit-cybertron/Verilog-RTL-Simulation-Repair-](https://github.com/ankit-cybertron/Verilog-RTL-Simulation-Repair-)

---

## 🎯 Motivation

RTL (Register-Transfer Level) hardware bugs cost semiconductor companies between $5M to $50M if they reach chip tapeout. Finding and repairing Verilog code before tapeout is critical. This OpenEnv benchmark challenges AI agents to take on the role of hardware verification engineers: reading compiler warnings, analyzing simulation outputs, and surgically patching Verilog syntax and state machine logic.

---

## 🏗️ Action and Observation Spaces

The environment strictly adheres to OpenEnv `Pydantic` spec types:

- **Action Space (`RTLAction`):**
  - `verilog_code` (str): The complete, repaired Verilog module rewritten by the AI.
  - `explanation` (str): Optional reasoning JSON snippet of what was changed and why.

- **Observation Space (`RTLObservation`):**
  - Context: `task_id`, `module_name`, `module_spec`, `broken_module`
  - Dynamic Feedback: `compile_error` (iverilog output), `sim_output` (vvp stdout), `test_vector_results` (per-test array pass/fail), `vectors_passed`, `vectors_total`.

---

## 📖 Evaluation Guide for Judges

To evaluate this environment, follow these steps to connect an agent and run the benchmark.

### 🔌 Connectivity
The environment exposes a standard OpenEnv WebSocket API. You can connect to it using the `OpenEnvClient` or the provided `client.py` in this repository.

- **WebSocket URL:** `wss://cybertronak-rtlrepair-env.hf.space/ws`
- **HTTP URL:** `https://cybertronak-rtlrepair-env.hf.space`

### 🧪 Running the Benchmark
You can run the full evaluation suite using the `inference.py` script provided.

1. **Configure Environment:**
   ```bash
   export OPENAI_API_KEY="sk-..."    # Your API Key
   export HF_TOKEN="hf_..."          # Your HF Token
   export HF_SPACE_URL="https://cybertronak-rtlrepair-env.hf.space"
   ```

2. **Execute Inference:**
   ```bash
   python inference.py
   ```

### 📊 Baseline Performance Scores
Using the bundled `inference.py` script running `llama-3.3-70b-versatile` over all tasks (Max Score: 0.99):

- **Easy (Compile/Syntax):** Baseline Score `0.99` (Successfully hits perfect logic ceiling on step 1 or 2)
- **Medium (ALU Operations):** Baseline Score `0.85 - 0.99` (Usually resolves operations within 2 steps)
- **Hard (FSM Transitions):** Baseline Score `0.20 - 0.60` (Frontier models often fail to identify combinatorial output overrides correctly)

---

## 🏗️ Benchmark Tasks

This environment provides a tiered difficulty progression based on real-world hardware bugs:

| Level | Task | Bug Type | Max Steps | Complexity |
| :--- | :--- | :--- | :--- | :--- |
| **Easy** | 4-bit Counter | Syntax & Ports | 3 | Missing signals, typos, sensitivity list errors. |
| **Medium** | 4-bit ALU | Logic & Ops | 5 | Wrong arithmetic/logical operators (+ vs -, & vs \|). |
| **Hard** | Traffic Light FSM | State & Timers | 7 | Missing state transitions, unregistered output logic. |

---

## 📏 Dynamic Reward Function

We use a **Deterministic Grading Engine** based on runtime `iverilog` AST compilation and simulation. Scores are rigidly clamped between `(0.01, 0.99)` to satisfy gradient requirements.

- **`+0.20` | Compilation Eval:** `+0.20` for perfect AST compilation. Scaled down to `0.10` if compiler warnings emit, and scales negatively based on error magnitude if it fails.
- **`+0.80` | Logic Execution:** Fractional ratio of total test vectors logically passed against the testbench framework.
- **`-0.10` | Zero-Logic Penalty:** If the module compiles perfectly but deliberately avoids logic (0 vectors pass), it triggers a destructive behaviour penalty.
- **`-0.20` | Retrial Stagnation:** Incremental attempt tracker deducts `-0.05` recursively if the agent continuously resubmits failing modules (spends compute without solving it).

---

**Developed for the Meta x PyTorch x Scaler OpenEnv Hackathon — Round 1.**
