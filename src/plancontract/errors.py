"""Structured validation failures for agent routing plans."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ValidationCode(StrEnum):
    """Machine-readable validation error codes for CI and eval harnesses."""

    UNKNOWN_AGENT = "unknown_agent"
    DUPLICATE_TASK_ID = "duplicate_task_id"
    EMPTY_TASK_ID = "empty_task_id"
    UNKNOWN_DEPENDENCY = "unknown_dependency"
    SELF_DEPENDENCY = "self_dependency"
    DEPENDENCY_CYCLE = "dependency_cycle"
    TASK_LIMIT_EXCEEDED = "task_limit_exceeded"
    TOPOLOGY_TASK_MISMATCH = "topology_task_mismatch"
    INSTRUCTION_TOO_LONG = "instruction_too_long"
    INVALID_EXTENSION = "invalid_extension"
    DEFERRED_HAS_TASKS = "deferred_has_tasks"


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """Single validation finding with optional structured context.

    Attributes:
        code: Machine-readable issue category.
        message: Human-readable explanation suitable for logs or CI output.
        task_id: Task associated with the issue, when applicable.
        field_name: Plan field associated with the issue, when applicable.
        context: Additional structured metadata for tooling.
    """

    code: ValidationCode
    message: str
    task_id: str | None = None
    field_name: str | None = None
    context: dict[str, Any] = field(default_factory=dict)


class PlanValidationError(Exception):
    """Raised when strict validation mode rejects a plan."""

    def __init__(self, issues: list[ValidationIssue]) -> None:
        """Initialize the exception from structured validation issues.

        Args:
            issues: Validation findings that caused the failure.
        """
        self.issues = issues
        preview = "; ".join(issue.message for issue in issues[:3])
        if len(issues) > 3:
            preview += f" (+{len(issues) - 3} more)"
        super().__init__(preview)


@dataclass(frozen=True, slots=True)
class ValidationReport:
    """Aggregate validation outcome for a plan or task list.

    Attributes:
        issues: Validation findings collected during validation.
    """

    issues: tuple[ValidationIssue, ...] = ()

    @property
    def ok(self) -> bool:
        """Indicate whether validation passed without findings.

        Returns:
            True when no issues were recorded.
        """
        return not self.issues

    @property
    def error_count(self) -> int:
        """Count validation findings.

        Returns:
            Number of recorded issues.
        """
        return len(self.issues)

    def raise_if_invalid(self) -> None:
        """Raise when validation failed.

        Raises:
            PlanValidationError: When one or more issues were recorded.
        """
        if not self.ok:
            raise PlanValidationError(list(self.issues))

    def by_code(self, code: ValidationCode) -> tuple[ValidationIssue, ...]:
        """Filter issues by validation code.

        Args:
            code: Validation code to match.

        Returns:
            Issues whose code equals the requested value.
        """
        return tuple(issue for issue in self.issues if issue.code == code)
