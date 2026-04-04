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

### 📊 Expected Output
Each task produces structured JSON logs. The final score is the **best reward** achieved across all steps in an episode (0.0 to 1.0).
- **Easy:** Compilation and base signals (Target: >0.60)
- **Medium:** ALU Logic & Operators (Target: >0.40)
- **Hard:** FSM State Transitions (Target: >0.20)

---

## 🏗️ Benchmark Tasks

This environment provides a tiered difficulty progression based on real-world hardware bugs:

| Level | Task | Bug Type | Max Steps | Complexity |
| :--- | :--- | :--- | :--- | :--- |
| **Easy** | 4-bit Counter | Syntax & Ports | 3 | Missing signals, typos, sensitivity list errors. |
| **Medium** | 4-bit ALU | Logic & Ops | 5 | Wrong arithmetic/logical operators (+ vs -, & vs \|). |
| **Hard** | Traffic Light FSM | State & Timers | 7 | Missing state transitions, unregistered output logic. |

---

## 📏 Reward Function

We use a **Deterministic Grading Engine** based on `iverilog`. Agents are scored 0.0 to 1.0 per step:

- **+0.20** | **Compilation:** Does the module compile without errors?
- **+0.05** | **Progress:** Per individual compiler error eliminated since the previous step.
- **+0.70** | **Simulation:** Fraction of test vectors passing (e.g., +0.35 if 50% pass).
- **+0.10** | **Surgical Precision:** Bonus for not modifying correct lines in the file.
- **-0.02** | **Efficiency:** Small penalty per step to encourage the fastest possible fix.

---

**Developed for the Meta x PyTorch x Scaler OpenEnv Hackathon — Round 1.**
