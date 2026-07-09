"""Configurable policy for plan validation and normalization."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class PlanPolicy:
    """Runtime constraints applied during validation and finalization.

    Attributes:
        allowed_agents: Agent IDs permitted in a plan. Empty means any non-empty ID.
        max_tasks: Maximum tasks allowed in one turn plan.
        max_instruction_chars: Maximum instruction length per task.
        max_summary_chars: Maximum plan summary length.
        require_task_ids: Whether every task must include a non-empty task ID.
        allowed_extension_keys: Optional whitelist for ``PlanTask.extensions`` keys.
    """

    allowed_agents: frozenset[str] = field(default_factory=frozenset)
    max_tasks: int = 3
    max_instruction_chars: int = 300
    max_summary_chars: int = 240
    require_task_ids: bool = True
    allowed_extension_keys: frozenset[str] | None = None

    @classmethod
    def demo(cls) -> PlanPolicy:
        """Build the bundled demo policy for example agents.

        Returns:
            Policy allowing travel, billing, IT, knowledge, and policy agents.
        """
        return cls(
            allowed_agents=frozenset(
                {
                    "travel_agent",
                    "billing_agent",
                    "it_support_agent",
                    "knowledge_agent",
                    "policy_agent",
                }
            ),
        )

    def agent_is_allowed(self, agent_id: str) -> bool:
        """Check whether an agent ID is permitted under this policy.

        Args:
            agent_id: Candidate agent identifier from planner output.

        Returns:
            True when the agent ID is non-empty and allowed by policy.
        """
        if not agent_id.strip():
            return False
        if not self.allowed_agents:
            return True
        return agent_id in self.allowed_agents

    def clamp_instruction(self, text: str) -> str:
        """Truncate instruction text to the configured character limit.

        Args:
            text: Instruction text to normalize.

        Returns:
            Instruction truncated to ``max_instruction_chars``.
        """
        return text[: self.max_instruction_chars]


def clamp_instruction(text: str, policy: PlanPolicy) -> str:
    """Truncate instruction text using a policy instance.

    Args:
        text: Instruction text to normalize.
        policy: Policy providing the maximum instruction length.

    Returns:
        Instruction truncated to the policy limit.
    """
    return policy.clamp_instruction(text)
