"""Ensure committed JSON schemas match current Pydantic models."""

from __future__ import annotations

import json
from pathlib import Path

from plancontract.models import AgentPlan, PlanDraft

ROOT = Path(__file__).resolve().parents[1]


def test_committed_draft_schema_matches_model():
    path = ROOT / "schemas" / "plan_draft.schema.json"
    committed = json.loads(path.read_text(encoding="utf-8"))
    assert committed == PlanDraft.model_json_schema()


def test_committed_plan_schema_matches_model():
    path = ROOT / "schemas" / "agent_plan.schema.json"
    committed = json.loads(path.read_text(encoding="utf-8"))
    assert committed == AgentPlan.model_json_schema()
