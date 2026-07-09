"""Merge tasks that target the same agent within one turn."""

from __future__ import annotations

from plancontract.models import PlanTask
from plancontract.policy import PlanPolicy, clamp_instruction


def _resolve_extension_value(values: list[object]) -> object | None:
    """Resolve a merged extension value from multiple task sources.

    Args:
        values: Candidate extension values from tasks sharing an agent.

    Returns:
        The shared non-empty value when all candidates agree, otherwise None.
    """
    distinct = {value for value in values if value not in (None, "", [], {})}
    if not distinct:
        return None
    if len(distinct) == 1:
        return next(iter(distinct))
    return None


def _group_tasks_by_agent(tasks: list[PlanTask]) -> tuple[list[str], dict[str, list[PlanTask]]]:
    """Group tasks by agent while preserving first-seen agent order.

    Args:
        tasks: Planner tasks in declaration order.

    Returns:
        Tuple of ordered agent IDs and grouped tasks.
    """
    agent_order: list[str] = []
    grouped: dict[str, list[PlanTask]] = {}
    for task in tasks:
        if task.agent_id not in grouped:
            agent_order.append(task.agent_id)
            grouped[task.agent_id] = []
        grouped[task.agent_id].append(task)
    return agent_order, grouped


def _build_merged_task(
    agent_id: str,
    group: list[PlanTask],
    task_id: str,
    policy: PlanPolicy,
) -> PlanTask:
    """Build one merged task for an agent group.

    Args:
        agent_id: Agent receiving the merged instruction.
        group: Source tasks scheduled for the same agent.
        task_id: New runtime task identifier.
        policy: Policy used to clamp merged instruction length.

    Returns:
        Merged runtime task with combined instruction and extensions.
    """
    instruction = "; ".join(task.instruction for task in group if task.instruction)
    instruction = clamp_instruction(instruction, policy)

    extension_keys = {key for task in group for key in task.extensions}
    merged_extensions = {
        key: _resolve_extension_value([task.extensions.get(key) for task in group])
        for key in extension_keys
    }
    merged_extensions = {
        key: value for key, value in merged_extensions.items() if value is not None
    }

    return PlanTask(
        task_id=task_id,
        agent_id=agent_id,
        instruction=instruction,
        depends_on=[],
        extensions=merged_extensions,
    )


def _remap_dependencies(
    merged_tasks: list[PlanTask],
    source_tasks: list[PlanTask],
    grouped: dict[str, list[PlanTask]],
    id_by_agent: dict[str, str],
) -> None:
    """Remap dependencies from source task IDs onto merged task IDs.

    Args:
        merged_tasks: Merged tasks whose ``depends_on`` fields are updated in place.
        source_tasks: Original planner tasks before merge.
        grouped: Source tasks grouped by agent ID.
        id_by_agent: Mapping from agent ID to merged task ID.
    """
    old_to_new = {task.task_id: id_by_agent[task.agent_id] for task in source_tasks if task.task_id}

    for merged in merged_tasks:
        remapped: list[str] = []
        seen: set[str] = set()
        for source in grouped[merged.agent_id]:
            for dependency_id in source.depends_on:
                target_id = old_to_new.get(dependency_id, dependency_id)
                if target_id != merged.task_id and target_id not in seen:
                    seen.add(target_id)
                    remapped.append(target_id)
        merged.depends_on = remapped


def merge_same_agent_tasks(
    tasks: list[PlanTask],
    policy: PlanPolicy | None = None,
) -> list[PlanTask]:
    """Collapse duplicate agent tasks into one task per agent.

    Instructions are concatenated in first-seen order and truncated to the
    policy limit. Dependencies are remapped onto merged task IDs. Conflicting
    extension values are dropped instead of silently choosing a winner.

    Args:
        tasks: Proposed tasks in planner order.
        policy: Optional policy for instruction truncation.

    Returns:
        Merged task list, or the original list when no merge was required.
    """
    if len(tasks) < 2:
        return tasks

    active_policy = policy or PlanPolicy()
    agent_order, grouped = _group_tasks_by_agent(tasks)
    if all(len(group) == 1 for group in grouped.values()):
        return tasks

    merged_tasks: list[PlanTask] = []
    id_by_agent: dict[str, str] = {}
    for index, agent_id in enumerate(agent_order, start=1):
        task_id = f"t{index}"
        id_by_agent[agent_id] = task_id
        merged_tasks.append(_build_merged_task(agent_id, grouped[agent_id], task_id, active_policy))

    _remap_dependencies(merged_tasks, tasks, grouped, id_by_agent)
    return merged_tasks
