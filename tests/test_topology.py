"""Tests for topology derivation and dependency-graph scheduling."""

from __future__ import annotations

import pytest
from tests.helpers import make_task

from plancontract.models import PlanTopology
from plancontract.topology import (
    build_task_index,
    derive_topology,
    topological_waves,
)


class TestBuildTaskIndex:
    def test_empty(self):
        assert build_task_index([]) == {}

    def test_rejects_missing_ids(self):
        with pytest.raises(ValueError, match="non-empty task_id"):
            build_task_index([make_task("", "travel_agent")])

    def test_rejects_duplicate_ids(self):
        with pytest.raises(ValueError, match="unique"):
            build_task_index([make_task("t1"), make_task("t1", "billing_agent")])


class TestTopologicalWaves:
    def test_single_task_one_wave(self):
        waves = topological_waves([make_task("t1")])
        assert len(waves) == 1
        assert len(waves[0]) == 1

    def test_parallel_tasks_one_wave(self):
        waves = topological_waves([make_task("t1"), make_task("t2", "billing_agent")])
        assert len(waves) == 1
        assert len(waves[0]) == 2

    def test_sequential_tasks_two_waves(self):
        waves = topological_waves(
            [make_task("t1"), make_task("t2", "billing_agent", depends_on=["t1"])]
        )
        assert len(waves) == 2

    def test_cycle_detected(self):
        tasks = [
            make_task("t1", depends_on=["t2"]),
            make_task("t2", "billing_agent", depends_on=["t1"]),
        ]
        with pytest.raises(ValueError, match="cycle"):
            topological_waves(tasks)

    def test_unknown_dependency(self):
        with pytest.raises(ValueError, match="unknown dependency"):
            topological_waves([make_task("t1", depends_on=["t9"])])

    def test_self_dependency(self):
        with pytest.raises(ValueError, match="cannot depend on itself"):
            topological_waves([make_task("t1", depends_on=["t1"])])


class TestDeriveTopology:
    def test_zero_tasks_deferred(self):
        assert derive_topology([]) == PlanTopology.DEFERRED

    def test_one_task_single(self):
        assert derive_topology([make_task("t1", "travel_agent")]) == PlanTopology.SINGLE

    def test_two_independent_parallel(self):
        tasks = [make_task("t1", "travel_agent"), make_task("t2", "billing_agent")]
        assert derive_topology(tasks) == PlanTopology.PARALLEL

    def test_three_independent_parallel(self):
        tasks = [
            make_task("t1", "travel_agent"),
            make_task("t2", "billing_agent"),
            make_task("t3", "it_support_agent"),
        ]
        assert derive_topology(tasks) == PlanTopology.PARALLEL

    def test_chain_sequential(self):
        tasks = [
            make_task("t1", "travel_agent"),
            make_task("t2", "billing_agent", depends_on=["t1"]),
        ]
        assert derive_topology(tasks) == PlanTopology.SEQUENTIAL

    def test_three_chain_sequential(self):
        tasks = [
            make_task("t1", "travel_agent"),
            make_task("t2", "billing_agent", depends_on=["t1"]),
            make_task("t3", "it_support_agent", depends_on=["t2"]),
        ]
        assert derive_topology(tasks) == PlanTopology.SEQUENTIAL

    def test_fan_in_mixed(self):
        tasks = [
            make_task("t1", "travel_agent"),
            make_task("t2", "billing_agent"),
            make_task("t3", "knowledge_agent", depends_on=["t1", "t2"]),
        ]
        assert derive_topology(tasks) == PlanTopology.MIXED

    def test_fan_out_mixed(self):
        tasks = [
            make_task("t1", "travel_agent"),
            make_task("t2", "billing_agent", depends_on=["t1"]),
            make_task("t3", "it_support_agent"),
        ]
        assert derive_topology(tasks) == PlanTopology.MIXED

    def test_cycle_raises(self):
        tasks = [
            make_task("t1", "travel_agent", depends_on=["t2"]),
            make_task("t2", "billing_agent", depends_on=["t1"]),
        ]
        with pytest.raises(ValueError, match="cycle"):
            derive_topology(tasks)
