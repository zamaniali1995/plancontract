"""Topology derivation and dependency-graph scheduling."""

from __future__ import annotations

from plancontract.models import PlanTask, PlanTopology


def build_task_index(tasks: list[PlanTask]) -> dict[str, PlanTask]:
    """Index tasks by non-empty task ID.

    Args:
        tasks: Plan tasks participating in dependency resolution.

    Returns:
        Mapping from task ID to task.

    Raises:
        ValueError: When task IDs are missing or duplicated.
    """
    if not tasks:
        return {}

    task_ids = [task.task_id for task in tasks]
    if any(not task_id for task_id in task_ids):
        raise ValueError("all tasks must have non-empty task_id values when dependencies are used")

    if len(set(task_ids)) != len(task_ids):
        raise ValueError("task_id values must be unique")

    return {task.task_id: task for task in tasks}


def build_dependency_graph(
    tasks: list[PlanTask],
    task_index: dict[str, PlanTask],
) -> tuple[dict[str, int], dict[str, list[str]]]:
    """Build indegree and child adjacency maps for dependency traversal.

    Args:
        tasks: Plan tasks participating in dependency resolution.
        task_index: Task lookup keyed by task ID.

    Returns:
        Tuple of indegree counts and child adjacency lists.

    Raises:
        ValueError: When a dependency is unknown or self-referential.
    """
    indegree = {task.task_id: 0 for task in tasks}
    children: dict[str, list[str]] = {task.task_id: [] for task in tasks}

    for task in tasks:
        for dependency_id in task.depends_on:
            if dependency_id not in task_index:
                raise ValueError(f"unknown dependency {dependency_id!r} for task {task.task_id!r}")
            if dependency_id == task.task_id:
                raise ValueError(f"task {task.task_id!r} cannot depend on itself")
            indegree[task.task_id] += 1
            children[dependency_id].append(task.task_id)

    return indegree, children


def topological_waves(
    tasks: list[PlanTask],
    *,
    task_index: dict[str, PlanTask] | None = None,
    indegree: dict[str, int] | None = None,
    children: dict[str, list[str]] | None = None,
) -> list[list[PlanTask]]:
    """Compute execution waves using Kahn's topological sort.

    Each wave contains tasks whose dependencies are satisfied by prior waves.
    Tasks inside a wave may execute concurrently.

    Args:
        tasks: Plan tasks to schedule.
        task_index: Optional pre-built task index.
        indegree: Optional pre-built indegree map.
        children: Optional pre-built child adjacency map.

    Returns:
        Topologically ordered waves of tasks.

    Raises:
        ValueError: When the dependency graph contains a cycle.
    """
    if not tasks:
        return []

    index = task_index or build_task_index(tasks)
    indegree_map, child_map = (
        (indegree, children)
        if indegree is not None and children is not None
        else build_dependency_graph(tasks, index)
    )

    remaining_indegree = dict(indegree_map)
    ready_ids = [task.task_id for task in tasks if remaining_indegree[task.task_id] == 0]
    waves: list[list[PlanTask]] = []
    processed_count = 0

    while ready_ids:
        current_wave_ids = list(ready_ids)
        ready_ids = []
        waves.append([index[task_id] for task_id in current_wave_ids])

        for task_id in current_wave_ids:
            processed_count += 1
            for child_id in child_map[task_id]:
                remaining_indegree[child_id] -= 1
                if remaining_indegree[child_id] == 0:
                    ready_ids.append(child_id)

    if processed_count != len(tasks):
        raise ValueError("dependency cycle detected")

    return waves


def derive_topology(tasks: list[PlanTask]) -> PlanTopology:
    """Infer execution topology from tasks and their dependencies.

    Topology is derived deterministically from the dependency graph:
    zero tasks map to deferred, one task to single, one wave to parallel,
    one task per wave to sequential, and all other valid shapes to mixed.

    Args:
        tasks: Proposed plan tasks after normalization.

    Returns:
        Derived execution topology.

    Raises:
        ValueError: When task IDs, dependency references, or cycles are invalid.
    """
    task_count = len(tasks)
    if task_count == 0:
        return PlanTopology.DEFERRED
    if task_count == 1:
        return PlanTopology.SINGLE

    task_index = build_task_index(tasks)
    indegree, child_map = build_dependency_graph(tasks, task_index)
    waves = topological_waves(
        tasks,
        task_index=task_index,
        indegree=indegree,
        children=child_map,
    )

    if len(waves) == 1:
        return PlanTopology.PARALLEL
    if all(len(wave) == 1 for wave in waves):
        return PlanTopology.SEQUENTIAL
    return PlanTopology.MIXED
