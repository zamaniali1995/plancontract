# Design Notes

PlanContract models one conversational turn in a multi-agent assistant:

1. A planner proposes tasks (`PlanDraft`).
2. Runtime code merges duplicate agents, derives topology, and validates (`finalize_draft`).
3. A dispatcher executes tasks in dependency waves (`execution_waves()`).

## Topology derivation

Topology is derived from the dependency graph, not trusted from the LLM:

| Tasks | Dependency shape | Topology |
| --- | --- | --- |
| 0 | — | `deferred` |
| 1 | — | `single` |
| 2–3 | one wave | `parallel` |
| 2–3 | one task per wave | `sequential` |
| 3 | fan-in / fan-out | `mixed` |

This makes shape/task-count mismatches structurally impossible after finalization.

## Validation layers

1. **Schema** — Pydantic field constraints
2. **Policy** — allowlisted agents, task limits, extension keys
3. **Topology** — unknown deps, self-deps, cycles (`topology.py`)
4. **Topology** — consistency between declared topology and task count

Validation returns a structured `ValidationReport` so CI and eval harnesses can gate merges without exceptions.

## Framework integration

PlanContract is runtime-agnostic. Framework adapters (LangGraph, Pydantic AI, CrewAI) should:

- Map LLM structured output → `PlanDraft`
- Call `finalize_draft(draft, policy=...)`
- Execute `plan.execution_waves()` with framework-native parallelism

## Demo domain

Examples use neutral agents (`travel_agent`, `billing_agent`, `it_support_agent`) rather than any product-specific catalog.
