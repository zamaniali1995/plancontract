"""PlanContract — framework-agnostic schemas for multi-agent turn routing."""

from plancontract.errors import (
    PlanValidationError,
    ValidationCode,
    ValidationIssue,
    ValidationReport,
)
from plancontract.finalize import finalize_draft
from plancontract.merge import merge_same_agent_tasks
from plancontract.models import (
    AgentPlan,
    AgentResult,
    Locale,
    PlanDraft,
    PlanTask,
    PlanTopology,
    TaskDraft,
)
from plancontract.policy import PlanPolicy
from plancontract.topology import (
    build_dependency_graph,
    build_task_index,
    derive_topology,
    topological_waves,
)
from plancontract.validate import validate_plan, validate_tasks

__all__ = [
    "AgentPlan",
    "AgentResult",
    "Locale",
    "PlanDraft",
    "PlanPolicy",
    "PlanTask",
    "PlanTopology",
    "PlanValidationError",
    "TaskDraft",
    "ValidationCode",
    "ValidationIssue",
    "ValidationReport",
    "build_dependency_graph",
    "build_task_index",
    "derive_topology",
    "finalize_draft",
    "merge_same_agent_tasks",
    "topological_waves",
    "validate_plan",
    "validate_tasks",
]

__version__ = "0.1.0"
