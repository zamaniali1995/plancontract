"""Shared pytest fixtures."""

from __future__ import annotations

import pytest

from plancontract.policy import PlanPolicy


@pytest.fixture
def demo_policy() -> PlanPolicy:
    """Return the bundled demo validation policy."""
    return PlanPolicy.demo()
