"""Shared test helpers."""

from __future__ import annotations

from plancontract.models import PlanTask


def make_task(
    task_id: str,
    agent_id: str = "travel_agent",
    depends_on: list[str] | None = None,
    instruction: str = "",
) -> PlanTask:
    """Build a plan task for tests."""
    return PlanTask(
        task_id=task_id,
        agent_id=agent_id,
        depends_on=depends_on or [],
        instruction=instruction,
    )
