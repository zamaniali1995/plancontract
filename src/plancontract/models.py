"""Pydantic models for agent routing plans."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Self

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator, model_validator


class PlanTopology(StrEnum):
    """Execution topology for a single conversational turn."""

    SINGLE = "single"
    PARALLEL = "parallel"
    SEQUENTIAL = "sequential"
    MIXED = "mixed"
    DEFERRED = "deferred"
    FALLBACK = "fallback"


class Locale(StrEnum):
    """Response locale hint carried with a plan."""

    EN = "en"
    FR = "fr"


class TaskSpec(BaseModel):
    """Shared task fields used by draft and runtime plan models."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    task_id: str = Field(default="", validation_alias=AliasChoices("task_id", "id"))
    agent_id: str
    instruction: str = Field(default="", max_length=300)
    depends_on: list[str] = Field(default_factory=list)
    extensions: dict[str, Any] = Field(default_factory=dict)

    @field_validator("task_id", "agent_id", "instruction", mode="before")
    @classmethod
    def _strip_optional_string(cls, value: Any) -> str:
        """Normalize nullable planner strings to stripped text.

        Args:
            value: Raw field value from JSON or Python input.

        Returns:
            Stripped string, or an empty string when the value is null.
        """
        if value is None:
            return ""
        return str(value).strip()

    @field_validator("depends_on")
    @classmethod
    def _dedupe_dependency_ids(cls, value: list[str]) -> list[str]:
        """Normalize dependency IDs while preserving first-seen order.

        Args:
            value: Raw dependency ID list from planner output.

        Returns:
            De-duplicated dependency IDs with empty entries removed.
        """
        seen: set[str] = set()
        normalized: list[str] = []
        for dependency_id in value:
            cleaned = str(dependency_id).strip()
            if cleaned and cleaned not in seen:
                seen.add(cleaned)
                normalized.append(cleaned)
        return normalized


class PlanTask(TaskSpec):
    """One agent invocation within a finalized turn plan."""


class TaskDraft(TaskSpec):
    """LLM-facing task proposal before runtime normalization."""

    def to_task(self) -> PlanTask:
        """Convert a draft task into a runtime plan task.

        Returns:
            Validated runtime task with identical field values.
        """
        return PlanTask.model_validate(self.model_dump())


class PlanDraft(BaseModel):
    """Minimal planner output containing proposed tasks and metadata."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    tasks: list[TaskDraft] = Field(default_factory=list)
    locale: Locale = Locale.EN
    summary: str = Field(default="", max_length=240)


class AgentPlan(BaseModel):
    """Validated routing plan for one conversational turn."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    tasks: list[PlanTask] = Field(default_factory=list)
    topology: PlanTopology = PlanTopology.SINGLE
    locale: Locale = Locale.EN
    title: str = ""

    @property
    def agent_ids(self) -> list[str]:
        """List agent IDs in task declaration order.

        Returns:
            Agent IDs, one entry per scheduled task.
        """
        return [task.agent_id for task in self.tasks]

    @property
    def is_multi_agent(self) -> bool:
        """Indicate whether more than one agent is scheduled.

        Returns:
            True when the plan contains multiple tasks.
        """
        return len(self.tasks) > 1

    @property
    def is_deferred(self) -> bool:
        """Indicate whether the turn intentionally schedules no agents.

        Returns:
            True when topology is deferred.
        """
        return self.topology == PlanTopology.DEFERRED

    def execution_waves(self) -> list[list[PlanTask]]:
        """Compute dependency-ordered execution waves for dispatch.

        Tasks within a wave have no unresolved dependencies and may run
        concurrently. Each subsequent wave waits for the previous wave.

        Returns:
            Topologically ordered task groups.

        Raises:
            ValueError: When task IDs are invalid or the graph contains a cycle.
        """
        from plancontract.topology import topological_waves

        return topological_waves(self.tasks)

    @model_validator(mode="after")
    def _assert_topology_matches_task_count(self) -> Self:
        """Reject structurally inconsistent topology and task-count pairs.

        Returns:
            Validated plan instance.

        Raises:
            ValueError: When topology constraints are violated.
        """
        task_count = len(self.tasks)
        if self.topology == PlanTopology.DEFERRED and task_count != 0:
            raise ValueError("deferred topology requires zero tasks")
        if self.topology == PlanTopology.SINGLE and task_count > 1:
            raise ValueError("single topology allows at most one task")
        if self.topology in {PlanTopology.PARALLEL, PlanTopology.SEQUENTIAL} and task_count not in {
            2,
            3,
        }:
            raise ValueError(f"{self.topology.value} topology requires two or three tasks")
        if self.topology == PlanTopology.MIXED and task_count != 3:
            raise ValueError("mixed topology requires exactly three tasks")
        return self


class AgentResult(BaseModel):
    """Normalized output from a completed agent invocation."""

    model_config = ConfigDict(extra="forbid")

    agent_id: str
    summary: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)
    tools_used: list[str] = Field(default_factory=list)
    has_error: bool = False
    timed_out: bool = False
    elapsed_ms: int | None = None
