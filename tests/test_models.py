"""Tests for pydantic models."""

from __future__ import annotations

import pytest

from plancontract.models import AgentPlan, PlanTask, PlanTopology


def test_task_accepts_id_alias():
    task = PlanTask.model_validate({"id": "t1", "agent_id": "travel_agent"})
    assert task.task_id == "t1"


def test_agent_plan_execution_waves():
    plan = AgentPlan(
        tasks=[
            PlanTask(task_id="t1", agent_id="travel_agent"),
            PlanTask(task_id="t2", agent_id="billing_agent", depends_on=["t1"]),
        ],
        topology=PlanTopology.SEQUENTIAL,
    )
    waves = plan.execution_waves()
    assert len(waves) == 2


def test_topology_validator_rejects_invalid_single():
    with pytest.raises(ValueError, match="single topology"):
        AgentPlan(
            tasks=[
                PlanTask(task_id="t1", agent_id="travel_agent"),
                PlanTask(task_id="t2", agent_id="billing_agent"),
            ],
            topology=PlanTopology.SINGLE,
        )
