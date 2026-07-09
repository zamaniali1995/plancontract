"""Integration tests for draft finalization."""

from __future__ import annotations

import pytest

from plancontract.errors import PlanValidationError
from plancontract.finalize import finalize_draft
from plancontract.models import Locale, PlanDraft, PlanTopology, TaskDraft
from plancontract.policy import PlanPolicy


class TestFinalizeDraft:
    def test_empty_draft_is_deferred(self):
        plan = finalize_draft(PlanDraft(tasks=[]), policy=PlanPolicy.demo())
        assert plan.topology == PlanTopology.DEFERRED
        assert plan.tasks == []

    def test_parallel_two_agents(self):
        draft = PlanDraft(
            tasks=[
                TaskDraft(task_id="t1", agent_id="travel_agent", instruction="find flights"),
                TaskDraft(task_id="t2", agent_id="billing_agent", instruction="check coverage"),
            ]
        )
        plan = finalize_draft(draft, policy=PlanPolicy.demo())
        assert plan.topology == PlanTopology.PARALLEL
        assert plan.agent_ids == ["travel_agent", "billing_agent"]

    def test_merges_duplicate_agents(self):
        draft = PlanDraft(
            tasks=[
                TaskDraft(task_id="t1", agent_id="travel_agent", instruction="tokyo"),
                TaskDraft(task_id="t2", agent_id="travel_agent", instruction="osaka"),
            ]
        )
        plan = finalize_draft(draft, policy=PlanPolicy.demo())
        assert plan.topology == PlanTopology.SINGLE
        assert len(plan.tasks) == 1

    def test_sequential_chain(self):
        draft = PlanDraft(
            tasks=[
                TaskDraft(task_id="t1", agent_id="travel_agent", instruction="pick destination"),
                TaskDraft(
                    task_id="t2",
                    agent_id="billing_agent",
                    instruction="confirm budget",
                    depends_on=["t1"],
                ),
            ]
        )
        plan = finalize_draft(draft, policy=PlanPolicy.demo())
        assert plan.topology == PlanTopology.SEQUENTIAL
        waves = plan.execution_waves()
        assert len(waves) == 2

    def test_unknown_agent_raises_in_strict_mode(self):
        draft = PlanDraft(
            tasks=[TaskDraft(task_id="t1", agent_id="rogue_agent", instruction="hack")]
        )
        with pytest.raises(PlanValidationError):
            finalize_draft(draft, policy=PlanPolicy.demo(), strict=True)

    def test_locale_preserved(self):
        draft = PlanDraft(
            tasks=[TaskDraft(task_id="t1", agent_id="travel_agent", instruction="vol")],
            locale=Locale.FR,
        )
        plan = finalize_draft(draft, policy=PlanPolicy.demo())
        assert plan.locale == Locale.FR
