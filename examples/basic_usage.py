#!/usr/bin/env python3
"""Example: finalize a planner draft into a validated agent plan."""

from __future__ import annotations

from plancontract import PlanDraft, PlanPolicy, TaskDraft, finalize_draft, validate_plan


def main() -> None:
    draft = PlanDraft(
        tasks=[
            TaskDraft(
                task_id="t1",
                agent_id="travel_agent",
                instruction="find direct flights to Tokyo next month",
            ),
            TaskDraft(
                task_id="t2",
                agent_id="billing_agent",
                instruction="check whether premium travel insurance is included",
            ),
        ],
        summary="Searching travel options and verifying billing coverage.",
    )

    policy = PlanPolicy.demo()
    plan = finalize_draft(draft, policy=policy)

    print("topology:", plan.topology.value)
    print("agents:", plan.agent_ids)
    print("waves:")
    for index, wave in enumerate(plan.execution_waves(), start=1):
        print(f"  wave {index}:", [task.agent_id for task in wave])

    report = validate_plan(plan, policy=policy)
    print("valid:", report.ok)


if __name__ == "__main__":
    main()
