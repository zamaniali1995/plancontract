"""End-to-end CLI and JSON schema smoke tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from plancontract.models import AgentPlan, PlanDraft

ROOT = Path(__file__).resolve().parents[1]


def test_json_schema_export():
    schema = PlanDraft.model_json_schema()
    assert "tasks" in schema["properties"]


def test_cli_validate_ok(tmp_path: Path):
    payload = {
        "tasks": [
            {"task_id": "t1", "agent_id": "travel_agent", "instruction": "find flights"},
            {"task_id": "t2", "agent_id": "billing_agent", "instruction": "check plan"},
        ],
        "topology": "parallel",
        "locale": "en",
        "title": "",
    }
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-m", "plancontract.cli", "validate", str(path), "--demo-policy"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_roundtrip_agent_plan():
    plan = AgentPlan.model_validate(
        {
            "tasks": [{"task_id": "t1", "agent_id": "travel_agent", "instruction": "help"}],
            "topology": "single",
        }
    )
    restored = AgentPlan.model_validate_json(plan.model_dump_json())
    assert restored == plan
