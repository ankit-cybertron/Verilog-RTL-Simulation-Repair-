"""
environment.py — RTLRepair-Env core environment logic

Implements the OpenEnv Environment base class with:
  reset()  → loads task, returns initial RTLObservation
  step()   → grades agent Verilog, returns scored RTLObservation
  state    → current episode State
"""

from uuid import uuid4
from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import RTLAction, RTLObservation
from server.grader import compute_reward, load_broken_module, get_task_config

DEFAULT_TASK = "easy"


class RTLRepairEnvironment(Environment):
    """
    RTL Repair Environment.

    Each episode presents the agent with a broken Verilog module.
    The agent must return repaired Verilog that passes iverilog
    compilation and simulation test vectors.
    """

    def __init__(self):
        self._state = State(episode_id=str(uuid4()), step_count=0)
        self._task_id: str = DEFAULT_TASK
        self._prev_error_count: int = 999
        self._task_config: dict = get_task_config(DEFAULT_TASK)
        self._broken_module: str = load_broken_module(DEFAULT_TASK)

    def reset(self, task_id: str = DEFAULT_TASK) -> RTLObservation:
        """
        Start a new episode for the given task.
        Returns a clean observation with the broken module and task spec.
        """
        if task_id not in ("easy", "medium", "hard"):
            task_id = DEFAULT_TASK

        self._task_id = task_id
        self._task_config = get_task_config(task_id)
        self._broken_module = load_broken_module(task_id)
        self._prev_error_count = 999
        self._state = State(episode_id=str(uuid4()), step_count=0)

        return RTLObservation(
            task_id=task_id,
            module_name=self._task_config["module_name"],
            module_spec=self._task_config["module_spec"],
            broken_module=self._broken_module,
            compile_error="",
            sim_output="",
            test_vector_results=[],
            vectors_passed=0,
            vectors_total=self._task_config["vectors_total"],
            step_count=0,
            max_steps=self._task_config["max_steps"],
            reward=0.0,
            done=False,
        )

    def step(self, action: RTLAction) -> RTLObservation:
        """
        Grade the agent's repaired Verilog.
        Runs iverilog compile + simulation, scores against golden output.
        Returns updated observation with reward and feedback.
        """
        self._state.step_count += 1
        current_step = self._state.step_count
        max_steps = self._task_config["max_steps"]

        # Grade the submission
        reward, compile_error, sim_output, vectors_passed, vectors_total, vector_results = (
            compute_reward(
                agent_verilog=action.verilog_code,
                task_id=self._task_id,
                prev_error_count=self._prev_error_count,
                current_step=current_step,
            )
        )

        # Track error count for next step's partial credit
        if compile_error:
            from server.grader import count_compile_errors
            self._prev_error_count = count_compile_errors(compile_error)
        else:
            self._prev_error_count = 0

        # Episode is done if fully solved or max steps reached
        done = (reward >= 0.90) or (current_step >= max_steps)

        return RTLObservation(
            task_id=self._task_id,
            module_name=self._task_config["module_name"],
            module_spec=self._task_config["module_spec"],
            broken_module=self._broken_module,
            compile_error=compile_error,
            sim_output=sim_output,
            test_vector_results=vector_results,
            vectors_passed=vectors_passed,
            vectors_total=vectors_total,
            step_count=current_step,
            max_steps=max_steps,
            reward=reward,
            done=done,
        )

    @property
    def state(self) -> State:
        return self._state