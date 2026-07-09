"""Semantic validation for agent routing plans."""

from __future__ import annotations

from plancontract.errors import ValidationCode, ValidationIssue, ValidationReport
from plancontract.models import AgentPlan, PlanTask, PlanTopology
from plancontract.policy import PlanPolicy
from plancontract.topology import build_dependency_graph, build_task_index, topological_waves


def _validate_topology_task_count(
    topology: PlanTopology,
    task_count: int,
) -> ValidationIssue | None:
    """Check whether topology constraints match the number of tasks.

    Args:
        topology: Declared execution topology.
        task_count: Number of tasks in the plan.

    Returns:
        Validation issue when the pair is inconsistent, otherwise None.
    """
    if topology == PlanTopology.DEFERRED and task_count != 0:
        return ValidationIssue(
            code=ValidationCode.DEFERRED_HAS_TASKS,
            message=f"topology 'deferred' requires 0 tasks, got {task_count}",
        )
    if topology == PlanTopology.SINGLE and task_count > 1:
        return ValidationIssue(
            code=ValidationCode.TOPOLOGY_TASK_MISMATCH,
            message=f"topology 'single' allows at most 1 task, got {task_count}",
        )
    if topology in {PlanTopology.PARALLEL, PlanTopology.SEQUENTIAL} and task_count not in {2, 3}:
        return ValidationIssue(
            code=ValidationCode.TOPOLOGY_TASK_MISMATCH,
            message=f"topology '{topology.value}' requires 2 or 3 tasks, got {task_count}",
            context={"topology": topology.value, "task_count": task_count},
        )
    if topology == PlanTopology.MIXED and task_count != 3:
        return ValidationIssue(
            code=ValidationCode.TOPOLOGY_TASK_MISMATCH,
            message=f"topology 'mixed' requires exactly 3 tasks, got {task_count}",
        )
    return None


def _validate_topology_shape_without_dependencies(
    topology: PlanTopology,
    task_count: int,
) -> ValidationIssue | None:
    """Check implicit topology shape when no dependencies are declared.

    Args:
        topology: Declared execution topology.
        task_count: Number of tasks in the plan.

    Returns:
        Validation issue when the shape is inconsistent, otherwise None.
    """
    expected_counts = {
        PlanTopology.SINGLE: task_count == 1,
        PlanTopology.SEQUENTIAL: task_count == 2,
        PlanTopology.MIXED: task_count == 3,
        PlanTopology.PARALLEL: task_count >= 2,
    }
    is_valid = expected_counts.get(topology)
    if is_valid is not None and not is_valid:
        return ValidationIssue(
            code=ValidationCode.TOPOLOGY_TASK_MISMATCH,
            message=f"topology '{topology.value}' is inconsistent with {task_count} task(s)",
            context={"topology": topology.value, "task_count": task_count},
        )
    return None


def _validate_task_limit(tasks: list[PlanTask], policy: PlanPolicy) -> ValidationIssue | None:
    """Check whether the task count exceeds policy limits.

    Args:
        tasks: Tasks to validate.
        policy: Active validation policy.

    Returns:
        Validation issue when the limit is exceeded, otherwise None.
    """
    if len(tasks) <= policy.max_tasks:
        return None
    return ValidationIssue(
        code=ValidationCode.TASK_LIMIT_EXCEEDED,
        message=f"plan contains {len(tasks)} tasks; limit is {policy.max_tasks}",
    )


def _validate_required_task_ids(
    tasks: list[PlanTask], policy: PlanPolicy
) -> ValidationIssue | None:
    """Check whether all tasks include non-empty IDs when required.

    Args:
        tasks: Tasks to validate.
        policy: Active validation policy.

    Returns:
        Validation issue when a required task ID is missing, otherwise None.
    """
    if not policy.require_task_ids or not tasks:
        return None
    if any(not task.task_id for task in tasks):
        return ValidationIssue(
            code=ValidationCode.EMPTY_TASK_ID,
            message="all tasks must include a non-empty task_id",
        )
    return None


def _validate_unique_task_ids(tasks: list[PlanTask]) -> list[ValidationIssue]:
    """Detect duplicate task IDs.

    Args:
        tasks: Tasks to validate.

    Returns:
        Issues for each duplicate task ID encountered.
    """
    issues: list[ValidationIssue] = []
    seen: set[str] = set()
    for task in tasks:
        if not task.task_id:
            continue
        if task.task_id in seen:
            issues.append(
                ValidationIssue(
                    code=ValidationCode.DUPLICATE_TASK_ID,
                    message=f"duplicate task_id {task.task_id!r}",
                    task_id=task.task_id,
                )
            )
        seen.add(task.task_id)
    return issues


def _validate_task_fields(tasks: list[PlanTask], policy: PlanPolicy) -> list[ValidationIssue]:
    """Validate per-task policy constraints.

    Args:
        tasks: Tasks to validate.
        policy: Active validation policy.

    Returns:
        Issues for disallowed agents, long instructions, or invalid extensions.
    """
    issues: list[ValidationIssue] = []
    for task in tasks:
        if not policy.agent_is_allowed(task.agent_id):
            issues.append(
                ValidationIssue(
                    code=ValidationCode.UNKNOWN_AGENT,
                    message=f"unknown or disallowed agent_id {task.agent_id!r}",
                    task_id=task.task_id or None,
                    field_name="agent_id",
                )
            )
        if len(task.instruction) > policy.max_instruction_chars:
            issues.append(
                ValidationIssue(
                    code=ValidationCode.INSTRUCTION_TOO_LONG,
                    message=f"instruction exceeds {policy.max_instruction_chars} characters",
                    task_id=task.task_id or None,
                    field_name="instruction",
                )
            )
        if policy.allowed_extension_keys is None:
            continue
        unknown_keys = set(task.extensions) - policy.allowed_extension_keys
        if unknown_keys:
            issues.append(
                ValidationIssue(
                    code=ValidationCode.INVALID_EXTENSION,
                    message=f"unsupported extension keys: {sorted(unknown_keys)}",
                    task_id=task.task_id or None,
                    field_name="extensions",
                    context={"keys": sorted(unknown_keys)},
                )
            )
    return issues


def _validate_dependency_references(tasks: list[PlanTask]) -> list[ValidationIssue]:
    """Validate dependency references and self-dependencies.

    Args:
        tasks: Tasks to validate.

    Returns:
        Issues for unknown or self-referential dependencies.
    """
    issues: list[ValidationIssue] = []
    known_ids = {task.task_id for task in tasks if task.task_id}
    for task in tasks:
        unknown_ids = set(task.depends_on) - known_ids
        if unknown_ids:
            issues.append(
                ValidationIssue(
                    code=ValidationCode.UNKNOWN_DEPENDENCY,
                    message=(
                        f"task {task.task_id!r} depends_on unknown ids: {sorted(unknown_ids)}"
                    ),
                    task_id=task.task_id or None,
                    field_name="depends_on",
                    context={"unknown": sorted(unknown_ids)},
                )
            )
        if task.task_id and task.task_id in task.depends_on:
            issues.append(
                ValidationIssue(
                    code=ValidationCode.SELF_DEPENDENCY,
                    message=f"task {task.task_id!r} depends on itself",
                    task_id=task.task_id,
                    field_name="depends_on",
                )
            )
    return issues


def _validate_dependency_graph(tasks: list[PlanTask]) -> ValidationIssue | None:
    """Detect cycles and unresolved graph errors not caught earlier.

    Args:
        tasks: Tasks to validate.

    Returns:
        Graph validation issue, otherwise None.
    """
    try:
        task_index = build_task_index(tasks)
        indegree, children = build_dependency_graph(tasks, task_index)
        topological_waves(
            tasks,
            task_index=task_index,
            indegree=indegree,
            children=children,
        )
    except ValueError as exc:
        message = str(exc)
        code = (
            ValidationCode.DEPENDENCY_CYCLE
            if "cycle" in message
            else ValidationCode.UNKNOWN_DEPENDENCY
        )
        return ValidationIssue(code=code, message=message)
    return None


def validate_tasks(
    tasks: list[PlanTask],
    policy: PlanPolicy | None = None,
) -> ValidationReport:
    """Validate tasks without requiring a full ``AgentPlan`` wrapper.

    Args:
        tasks: Tasks to validate.
        policy: Optional policy constraints. Defaults to unrestricted policy.

    Returns:
        Structured validation report containing zero or more issues.
    """
    active_policy = policy or PlanPolicy()
    issues: list[ValidationIssue] = []

    for check in (
        _validate_task_limit(tasks, active_policy),
        _validate_required_task_ids(tasks, active_policy),
    ):
        if check is not None:
            issues.append(check)

    issues.extend(_validate_unique_task_ids(tasks))
    issues.extend(_validate_task_fields(tasks, active_policy))
    issues.extend(_validate_dependency_references(tasks))

    if not any(issue.code == ValidationCode.UNKNOWN_DEPENDENCY for issue in issues):
        graph_issue = _validate_dependency_graph(tasks)
        if graph_issue is not None:
            issues.append(graph_issue)

    return ValidationReport(issues=tuple(issues))


def validate_plan(
    plan: AgentPlan,
    policy: PlanPolicy | None = None,
) -> ValidationReport:
    """Validate a full agent plan including topology consistency.

    Args:
        plan: Finalized or candidate plan to validate.
        policy: Optional policy constraints. Defaults to unrestricted policy.

    Returns:
        Structured validation report containing zero or more issues.
    """
    issues = list(validate_tasks(plan.tasks, policy=policy).issues)

    topology_issue = _validate_topology_task_count(plan.topology, len(plan.tasks))
    if topology_issue is not None:
        issues.append(topology_issue)

    has_dependencies = any(task.depends_on for task in plan.tasks)
    if not has_dependencies:
        shape_issue = _validate_topology_shape_without_dependencies(
            plan.topology,
            len(plan.tasks),
        )
        if shape_issue is not None:
            issues.append(shape_issue)

    return ValidationReport(issues=tuple(issues))
