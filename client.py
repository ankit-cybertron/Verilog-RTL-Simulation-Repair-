"""
client.py — RTLRepairEnv WebSocket client

Usage:
    # Async
    async with RTLRepairEnv(base_url="https://your-space.hf.space") as env:
        result = await env.reset(task_id="easy")
        result = await env.step(RTLAction(verilog_code="module ...", explanation=""))

    # Sync wrapper
    with RTLRepairEnv(base_url="https://your-space.hf.space").sync() as env:
        result = env.reset(task_id="easy")
        result = env.step(RTLAction(verilog_code="module ...", explanation=""))
"""

from openenv.core.env_client import EnvClient
from openenv.core.client_types import StepResult
from openenv.core.env_server.types import State
from models import RTLAction, RTLObservation


class RTLRepairEnv(EnvClient[RTLAction, RTLObservation, State]):
    """
    WebSocket client for RTLRepair-Env.
    Connects to the FastAPI server running in Docker or HF Spaces.
    """

    def _step_payload(self, action: RTLAction) -> dict:
        return {
            "verilog_code": action.verilog_code,
            "explanation": action.explanation,
        }

    def _parse_result(self, payload: dict) -> StepResult[RTLObservation]:
        obs_data = payload.get("observation", {})
        obs = RTLObservation(
            task_id=obs_data.get("task_id", "easy"),
            module_name=obs_data.get("module_name", ""),
            module_spec=obs_data.get("module_spec", ""),
            broken_module=obs_data.get("broken_module", ""),
            compile_error=obs_data.get("compile_error", ""),
            sim_output=obs_data.get("sim_output", ""),
            test_vector_results=obs_data.get("test_vector_results", []),
            vectors_passed=obs_data.get("vectors_passed", 0),
            vectors_total=obs_data.get("vectors_total", 0),
            step_count=obs_data.get("step_count", 0),
            max_steps=obs_data.get("max_steps", 3),
            reward=obs_data.get("reward", 0.0),
            done=payload.get("done", False),
            episode_id=obs_data.get("episode_id", ""),
        )
        return StepResult(
            observation=obs,
            reward=payload.get("reward"),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: dict) -> State:
        return State(
            episode_id=payload.get("episode_id", ""),
            step_count=payload.get("step_count", 0),
        )