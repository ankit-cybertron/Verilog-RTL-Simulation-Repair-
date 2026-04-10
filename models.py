# models.py
# RTLRepair-Env — Pydantic models for action and observation spaces

from pydantic import Field
from typing import List
from openenv.core.env_server.types import Action, Observation


class RTLAction(Action):
    """
    The action the agent takes — a repaired Verilog module.
    The agent receives a broken Verilog module in the observation
    and must return a corrected version here.
    """
    verilog_code: str = Field(
        ...,
        description=(
            "The complete repaired Verilog module. Must be valid Verilog "
            "that iverilog can compile. Return the FULL module, not just changed lines."
        )
    )
    explanation: str = Field(
        default="",
        description="Optional explanation of what was fixed. Not graded, logged for analysis."
    )


class RTLObservation(Observation):
    """
    What the agent sees at each step — broken module, spec,
    compile errors, simulation output, and per-test-vector results.
    """
    # Task context
    task_id: str = Field(..., description="Task: 'easy' | 'medium' | 'hard'")
    module_name: str = Field(..., description="Name of the Verilog module to repair")
    module_spec: str = Field(
        ...,
        description=(
            "Natural language description of what the module SHOULD do. "
            "Use this to understand the intended behavior before fixing."
        )
    )
    broken_module: str = Field(
        ...,
        description="The broken Verilog module. Contains injected bugs."
    )

    # Feedback from previous step (empty on first step)
    compile_error: str = Field(
        default="",
        description=(
            "Output from iverilog. Empty = compiled OK. "
            "Non-empty = errors to fix."
        )
    )
    sim_output: str = Field(
        default="",
        description="Simulation stdout. Empty if compilation failed."
    )
    test_vector_results: List[dict] = Field(
        default_factory=list,
        description="Per-test-vector pass/fail. Each dict: vector_id, passed, expected, actual."
    )
    vectors_passed: int = Field(default=0, description="Test vectors that passed last step.")
    vectors_total: int = Field(default=0, description="Total test vectors for this task.")

    # Episode state
    step_count: int = Field(default=0, description="Steps taken in this episode.")
    max_steps: int = Field(..., description="Max steps allowed before episode ends.")
    reward: float = Field(default=0.02, description="Reward earned last step. Range 0.0-1.0.")
    done: bool = Field(default=False, description="True if episode is complete.")
    episode_id: str = Field(default="", description="Unique episode identifier.")