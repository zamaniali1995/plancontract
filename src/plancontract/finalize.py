"""Finalize LLM planner drafts into validated agent plans."""

from __future__ import annotations

from plancontract.merge import merge_same_agent_tasks
from plancontract.models import AgentPlan, PlanDraft, PlanTask
from plancontract.policy import PlanPolicy
from plancontract.topology import derive_topology
from plancontract.validate import validate_plan


def finalize_draft(
    draft: PlanDraft,
    *,
    policy: PlanPolicy | None = None,
    merge_agents: bool = True,
    strict: bool = True,
) -> AgentPlan:
    """Convert a planner draft into a validated agent plan.

    The pipeline converts draft tasks to runtime tasks, optionally merges
    duplicate agent assignments, derives topology from the dependency graph,
    and validates the result against policy and structural rules.

    Args:
        draft: LLM planner output.
        policy: Optional validation policy. Defaults to unrestricted policy.
        merge_agents: Whether to merge tasks that target the same agent ID.
        strict: Whether to raise when validation fails.

    Returns:
        Finalized agent plan ready for dispatch.

    Raises:
        PlanValidationError: When ``strict`` is True and validation fails.
    """
    active_policy = policy or PlanPolicy()
    tasks: list[PlanTask] = [task.to_task() for task in draft.tasks]

    if merge_agents:
        tasks = merge_same_agent_tasks(tasks, policy=active_policy)

    plan = AgentPlan(
        tasks=tasks,
        topology=derive_topology(tasks),
        locale=draft.locale,
        title="",
    )

    report = validate_plan(plan, policy=active_policy)
    if strict:
        report.raise_if_invalid()

    return plan
