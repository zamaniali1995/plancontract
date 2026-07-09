"""CLI tests."""

from __future__ import annotations

import json
import subprocess
import sys
from argparse import Namespace
from pathlib import Path

import pytest

from plancontract.cli import _cmd_finalize, _cmd_schema, _cmd_validate, _load_json_object, main

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples" / "data"


class TestCliHandlers:
    def test_cmd_schema_draft(self):
        assert _cmd_schema(Namespace(target="draft")) == 0

    def test_cmd_validate_plan_file(self, tmp_path: Path):
        payload = {
            "tasks": [
                {"task_id": "t1", "agent_id": "travel_agent", "instruction": "go"},
                {"task_id": "t2", "agent_id": "billing_agent", "instruction": "pay"},
            ],
            "topology": "parallel",
            "locale": "en",
            "title": "",
        }
        path = tmp_path / "plan.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        assert _cmd_validate(Namespace(file=str(path), mode="plan", demo_policy=True)) == 0

    def test_cmd_finalize_draft_file(self, tmp_path: Path):
        payload = {
            "tasks": [
                {"task_id": "t1", "agent_id": "travel_agent", "instruction": "go"},
                {
                    "task_id": "t2",
                    "agent_id": "billing_agent",
                    "instruction": "pay",
                    "depends_on": ["t1"],
                },
            ]
        }
        path = tmp_path / "draft.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        assert _cmd_finalize(Namespace(file=str(path), demo_policy=True)) == 0

    def test_load_json_missing_file(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError, match="file not found"):
            _load_json_object(tmp_path / "missing.json")

    def test_load_json_invalid_json(self, tmp_path: Path):
        path = tmp_path / "bad.json"
        path.write_text("{not json", encoding="utf-8")
        with pytest.raises(ValueError, match="invalid JSON"):
            _load_json_object(path)

    def test_load_json_non_object_root(self, tmp_path: Path):
        path = tmp_path / "array.json"
        path.write_text("[]", encoding="utf-8")
        with pytest.raises(ValueError, match="JSON object"):
            _load_json_object(path)

    def test_cmd_validate_missing_file(self, tmp_path: Path):
        code = _cmd_validate(
            Namespace(file=str(tmp_path / "missing.json"), mode="plan", demo_policy=False)
        )
        assert code == 2

    def test_cmd_finalize_validation_failure(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ):
        payload = {"tasks": [{"task_id": "t1", "agent_id": "unknown_agent", "instruction": "go"}]}
        path = tmp_path / "draft.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        code = _cmd_finalize(Namespace(file=str(path), demo_policy=True))
        assert code == 1
        body = json.loads(capsys.readouterr().out)
        assert body["ok"] is False
        assert body["issues"][0]["code"] == "unknown_agent"

    def test_main_help(self):
        with pytest.raises(SystemExit) as exc:
            main(["--help"])
        assert exc.value.code == 0


class TestCliSubprocess:
    def test_cli_help(self):
        result = subprocess.run(
            [sys.executable, "-m", "plancontract", "--help"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0
        assert "validate" in result.stdout

    def test_cli_module_entrypoint(self):
        result = subprocess.run(
            [sys.executable, "-m", "plancontract", "schema", "plan"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0

    def test_cli_validate_draft_mode(self, tmp_path: Path):
        payload = {
            "tasks": [
                {"task_id": "t1", "agent_id": "travel_agent", "instruction": "go"},
                {"task_id": "t2", "agent_id": "billing_agent", "instruction": "pay"},
            ]
        }
        path = tmp_path / "draft.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "plancontract",
                "validate",
                str(path),
                "--mode",
                "draft",
                "--demo-policy",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr

    def test_cli_finalize_sequential(self, tmp_path: Path):
        payload = json.loads((EXAMPLES / "plan_draft.sequential.json").read_text(encoding="utf-8"))
        path = tmp_path / "draft.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        result = subprocess.run(
            [sys.executable, "-m", "plancontract", "finalize", str(path), "--demo-policy"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        body = json.loads(result.stdout)
        assert body["topology"] == "sequential"

    def test_cli_schema(self):
        result = subprocess.run(
            [sys.executable, "-m", "plancontract", "schema", "draft"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0
        schema = json.loads(result.stdout)
        assert "tasks" in schema["properties"]
