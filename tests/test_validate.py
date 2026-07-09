"""Tests for plan validation."""

from __future__ import annotations

from tests.helpers import make_task

from plancontract.errors import ValidationCode
from plancontract.models import AgentPlan, PlanTopology
from plancontract.policy import PlanPolicy
from plancontract.validate import validate_plan, validate_tasks


class TestValidateTasks:
    def test_valid_parallel_tasks(self, demo_policy: PlanPolicy):
        report = validate_tasks(
            [make_task("t1"), make_task("t2", "billing_agent")],
            policy=demo_policy,
        )
        assert report.ok

    def test_unknown_agent(self, demo_policy: PlanPolicy):
        report = validate_tasks([make_task("t1", "unknown_agent")], policy=demo_policy)
        assert not report.ok
        assert report.by_code(ValidationCode.UNKNOWN_AGENT)

    def test_task_limit(self, demo_policy: PlanPolicy):
        policy = PlanPolicy(allowed_agents=demo_policy.allowed_agents, max_tasks=2)
        report = validate_tasks(
            [
                make_task("t1"),
                make_task("t2", "billing_agent"),
                make_task("t3", "it_support_agent"),
            ],
            policy=policy,
        )
        assert report.by_code(ValidationCode.TASK_LIMIT_EXCEEDED)

    def test_unknown_dependency(self, demo_policy: PlanPolicy):
        report = validate_tasks([make_task("t1", depends_on=["t9"])], policy=demo_policy)
        assert report.by_code(ValidationCode.UNKNOWN_DEPENDENCY)

    def test_open_policy_allows_any_agent(self):
        report = validate_tasks([make_task("t1", "custom_agent")])
        assert report.ok

    def test_instruction_length_violation(self):
        from plancontract.models import PlanTask

        task = PlanTask.model_construct(task_id="t1", agent_id="a", instruction="x" * 301)
        report = validate_tasks([task], policy=PlanPolicy(max_tasks=3))
        assert report.by_code(ValidationCode.INSTRUCTION_TOO_LONG)

    def test_extension_whitelist(self):
        policy = PlanPolicy(allowed_extension_keys=frozenset({"region"}))
        task = make_task("t1", "a")
        task.extensions = {"secret": 1}
        report = validate_tasks([task], policy=policy)
        assert report.by_code(ValidationCode.INVALID_EXTENSION)

    def test_cycle_reported(self):
        tasks = [
            make_task("t1", "a", depends_on=["t2"]),
            make_task("t2", "b", depends_on=["t1"]),
        ]
        report = validate_tasks(tasks)
        assert report.by_code(ValidationCode.DEPENDENCY_CYCLE)


class TestValidatePlan:
    def test_topology_mismatch_parallel_with_one_task(self, demo_policy: PlanPolicy):
        plan = AgentPlan.model_construct(
            tasks=[make_task("t1")],
            topology=PlanTopology.PARALLEL,
        )
        report = validate_plan(plan, policy=demo_policy)
        assert report.by_code(ValidationCode.TOPOLOGY_TASK_MISMATCH)

    def test_deferred_requires_zero_tasks(self, demo_policy: PlanPolicy):
        plan = AgentPlan.model_construct(
            tasks=[make_task("t1")],
            topology=PlanTopology.DEFERRED,
        )
        report = validate_plan(plan, policy=demo_policy)
        assert report.by_code(ValidationCode.DEFERRED_HAS_TASKS)

    def test_consistent_plan_passes(self, demo_policy: PlanPolicy):
        plan = AgentPlan(
            tasks=[make_task("t1"), make_task("t2", "billing_agent")],
            topology=PlanTopology.PARALLEL,
        )
        report = validate_plan(plan, policy=demo_policy)
        assert report.ok
