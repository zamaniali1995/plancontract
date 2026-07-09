"""Tests for same-agent task merging."""

from __future__ import annotations

from plancontract.merge import merge_same_agent_tasks
from plancontract.models import PlanTask, PlanTopology
from plancontract.topology import derive_topology


def _task(
    task_id: str,
    agent_id: str,
    instruction: str = "x",
    depends_on: list[str] | None = None,
    **extensions: object,
) -> PlanTask:
    return PlanTask(
        task_id=task_id,
        agent_id=agent_id,
        instruction=instruction,
        depends_on=depends_on or [],
        extensions=dict(extensions),
    )


class TestMergeSameAgentTasks:
    def test_noop_when_all_agents_unique(self):
        tasks = [_task("t1", "travel_agent"), _task("t2", "billing_agent", depends_on=["t1"])]
        assert merge_same_agent_tasks(tasks) is tasks

    def test_merges_instructions(self):
        tasks = [
            _task("t1", "travel_agent", "find flights"),
            _task("t2", "travel_agent", "compare fares"),
        ]
        merged = merge_same_agent_tasks(tasks)
        assert len(merged) == 1
        assert merged[0].instruction == "find flights; compare fares"
        assert derive_topology(merged) == PlanTopology.SINGLE

    def test_remaps_dependencies(self):
        tasks = [
            _task("t1", "billing_agent", "check plan"),
            _task("t2", "billing_agent", "list invoices"),
            _task("t3", "it_support_agent", "reset vpn", depends_on=["t2"]),
        ]
        merged = merge_same_agent_tasks(tasks)
        assert [task.agent_id for task in merged] == ["billing_agent", "it_support_agent"]
        assert merged[1].depends_on == ["t1"]
        assert derive_topology(merged) == PlanTopology.SEQUENTIAL

    def test_conflicting_extensions_cleared(self):
        tasks = [
            _task("t1", "billing_agent", "a", tier="pro"),
            _task("t2", "billing_agent", "b", tier="basic"),
        ]
        merged = merge_same_agent_tasks(tasks)
        assert merged[0].extensions == {}

    def test_agreeing_extensions_preserved(self):
        tasks = [
            _task("t1", "billing_agent", "a", region="ca"),
            _task("t2", "billing_agent", "b", region="ca"),
        ]
        merged = merge_same_agent_tasks(tasks)
        assert merged[0].extensions == {"region": "ca"}

    def test_instruction_truncated_to_policy(self):
        tasks = [_task("t1", "travel_agent", "a" * 200), _task("t2", "travel_agent", "b" * 200)]
        merged = merge_same_agent_tasks(tasks)
        assert len(merged[0].instruction) == 300
