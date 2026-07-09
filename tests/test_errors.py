"""Tests for validation report helpers."""

from __future__ import annotations

import pytest

from plancontract.errors import (
    PlanValidationError,
    ValidationCode,
    ValidationIssue,
    ValidationReport,
)


def test_report_raise_if_invalid():
    report = ValidationReport(
        issues=(
            ValidationIssue(code=ValidationCode.UNKNOWN_AGENT, message="bad agent", task_id="t1"),
        )
    )
    with pytest.raises(PlanValidationError) as exc:
        report.raise_if_invalid()
    assert len(exc.value.issues) == 1


def test_report_by_code():
    issue = ValidationIssue(code=ValidationCode.DEPENDENCY_CYCLE, message="cycle")
    report = ValidationReport(issues=(issue,))
    assert report.by_code(ValidationCode.DEPENDENCY_CYCLE)[0] is issue
