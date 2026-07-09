# Changelog

## 0.1.0 — 2026-07-09

### Added

- `AgentPlan`, `PlanTask`, `PlanDraft`, and `TaskDraft` Pydantic models
- `PlanTopology` enum: single, parallel, sequential, mixed, deferred, fallback
- Dependency graph utilities with Kahn topological waves
- `derive_topology()` from task dependency structure
- `merge_same_agent_tasks()` with extension conflict handling
- `validate_plan()` / `validate_tasks()` with structured `ValidationReport`
- `PlanPolicy` for agent allowlists and turn limits
- `finalize_draft()` pipeline for LLM planner output
- CLI: `plancontract validate`, `finalize`, and `schema`
- Committed JSON Schemas under `schemas/`
- Pre-commit hooks, Makefile, Dependabot, CONTRIBUTING, SECURITY
- uv for reproducible dev environments (`uv.lock`)
- Consolidated `topology.py` module and snake_case schema/example naming
- Comprehensive pytest suite and GitHub Actions CI (lint, typecheck, test, build)
