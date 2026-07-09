"""Command-line interface for PlanContract."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from plancontract.errors import PlanValidationError, ValidationIssue
from plancontract.finalize import finalize_draft
from plancontract.models import AgentPlan, PlanDraft
from plancontract.policy import PlanPolicy
from plancontract.validate import validate_plan

_EXIT_OK = 0
_EXIT_VALIDATION_FAILED = 1
_EXIT_USAGE_ERROR = 2


def _load_json_object(path: Path) -> dict[str, Any]:
    """Load a JSON object from disk.

    Args:
        path: Path to a JSON file.

    Returns:
        Parsed JSON object.

    Raises:
        FileNotFoundError: When the file does not exist.
        ValueError: When the file is not valid JSON or not an object.
    """
    if not path.is_file():
        raise FileNotFoundError(f"file not found: {path}")
    try:
        data: Any = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {path}: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise ValueError("expected a JSON object at the root")
    return data


def _emit_error_json(message: str) -> None:
    """Write a structured CLI error payload to stderr.

    Args:
        message: Human-readable error description.
    """
    print(json.dumps({"ok": False, "error": message}, indent=2), file=sys.stderr)


def _resolve_policy(use_demo_policy: bool) -> PlanPolicy:
    """Select the validation policy for a CLI command.

    Args:
        use_demo_policy: Whether to apply the bundled demo allowlist.

    Returns:
        Selected plan policy.
    """
    return PlanPolicy.demo() if use_demo_policy else PlanPolicy()


def _serialize_issues(issues: list[ValidationIssue]) -> list[dict[str, Any]]:
    """Convert validation issues into JSON-serializable dictionaries.

    Args:
        issues: Validation findings to serialize.

    Returns:
        Issue payloads suitable for CLI output.
    """
    return [
        {
            "code": issue.code.value,
            "message": issue.message,
            "task_id": issue.task_id,
            "field_name": issue.field_name,
            "context": issue.context,
        }
        for issue in issues
    ]


def _cmd_validate(args: argparse.Namespace) -> int:
    """Validate a plan or draft JSON file.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Process exit code.
    """
    try:
        payload = _load_json_object(Path(args.file))
    except (FileNotFoundError, ValueError) as exc:
        _emit_error_json(str(exc))
        return _EXIT_USAGE_ERROR

    policy = _resolve_policy(args.demo_policy)
    try:
        if args.mode == "draft":
            plan = finalize_draft(PlanDraft.model_validate(payload), policy=policy, strict=False)
        else:
            plan = AgentPlan.model_validate(payload)
    except ValidationError as exc:
        _emit_error_json(str(exc))
        return _EXIT_USAGE_ERROR

    report = validate_plan(plan, policy=policy)
    print(
        json.dumps(
            {
                "ok": report.ok,
                "error_count": report.error_count,
                "issues": _serialize_issues(list(report.issues)),
            },
            indent=2,
        )
    )
    return _EXIT_OK if report.ok else _EXIT_VALIDATION_FAILED


def _cmd_finalize(args: argparse.Namespace) -> int:
    """Finalize a planner draft into a validated agent plan.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Process exit code.
    """
    try:
        payload = _load_json_object(Path(args.file))
    except (FileNotFoundError, ValueError) as exc:
        _emit_error_json(str(exc))
        return _EXIT_USAGE_ERROR

    policy = _resolve_policy(args.demo_policy)
    try:
        plan = finalize_draft(PlanDraft.model_validate(payload), policy=policy, strict=True)
    except PlanValidationError as exc:
        print(
            json.dumps(
                {"ok": False, "issues": _serialize_issues(exc.issues)},
                indent=2,
            )
        )
        return _EXIT_VALIDATION_FAILED
    except ValidationError as exc:
        _emit_error_json(str(exc))
        return _EXIT_USAGE_ERROR

    print(plan.model_dump_json(indent=2))
    return _EXIT_OK


def _cmd_schema(args: argparse.Namespace) -> int:
    """Print JSON Schema for a plan model.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Process exit code.
    """
    schemas = {
        "draft": PlanDraft.model_json_schema(),
        "plan": AgentPlan.model_json_schema(),
    }
    print(json.dumps(schemas[args.target], indent=2))
    return _EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    """Build the PlanContract CLI argument parser.

    Returns:
        Configured argument parser with validate, finalize, and schema commands.
    """
    parser = argparse.ArgumentParser(
        prog="plancontract",
        description="Validate and finalize multi-agent routing plans",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="Validate a plan or draft JSON file")
    validate_parser.add_argument("file", help="Path to JSON plan or draft")
    validate_parser.add_argument(
        "--mode",
        choices=("plan", "draft"),
        default="plan",
        help="Interpret input as a finalized plan or LLM draft",
    )
    validate_parser.add_argument(
        "--demo-policy",
        action="store_true",
        help="Apply the bundled demo agent allowlist",
    )
    validate_parser.set_defaults(func=_cmd_validate)

    finalize_parser = subparsers.add_parser(
        "finalize",
        help="Finalize a planner draft into an agent plan",
    )
    finalize_parser.add_argument("file", help="Path to draft JSON")
    finalize_parser.add_argument(
        "--demo-policy",
        action="store_true",
        help="Apply the bundled demo agent allowlist",
    )
    finalize_parser.set_defaults(func=_cmd_finalize)

    schema_parser = subparsers.add_parser("schema", help="Print JSON Schema for plan models")
    schema_parser.add_argument("target", choices=("draft", "plan"))
    schema_parser.set_defaults(func=_cmd_schema)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the PlanContract CLI.

    Args:
        argv: Optional argument vector. Defaults to ``sys.argv[1:]``.

    Returns:
        Process exit code.
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
