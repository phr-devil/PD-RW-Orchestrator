"""Developer CLI; PD-RW read-only inspection and local operational plans only."""
from __future__ import annotations
import argparse
import json
import sqlite3
from pathlib import Path

from .controller import run_demo
from .integrations.pdrw import inspect_resume, pdrw_status
from .planner import demo_plan
from .policy import load_policy, compile_guidance
from .models import TaskPacket
from .registry import load_agents
from .runtime.store import assess_recovery, inspect_plan, mark_intent_uncertain, stage_plan


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_plan_file(path: str) -> tuple[str, tuple[TaskPacket, ...]]:
    source = Path(path)
    if not source.is_file() or source.stat().st_size > 128 * 1024:
        raise ValueError("PLAN_FILE_MISSING_OR_TOO_LARGE")
    obj = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(obj, dict) or set(obj) != {"schema_version", "plan_id", "tasks"}:
        raise ValueError("PLAN_FILE_INVALID_SHAPE")
    if obj["schema_version"] != "1.0" or not isinstance(obj["tasks"], list):
        raise ValueError("PLAN_FILE_SCHEMA_INVALID")
    if not 1 <= len(obj["tasks"]) <= 64:
        raise ValueError("PLAN_TASK_COUNT_INVALID")
    if any(not isinstance(row, dict) for row in obj["tasks"]):
        raise ValueError("PLAN_TASK_INVALID")
    return obj["plan_id"], tuple(TaskPacket(**row) for row in obj["tasks"])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pdrw-orch", description="PD-RW operational orchestrator (mock-only execution)")
    parser.add_argument("--agents", default=str(_repository_root() / "configs/agents.example.yaml"))
    parser.add_argument("--policy", default=str(_repository_root() / "policies/user/research-guidance.example.yaml"))
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor")
    agents = commands.add_parser("agents")
    agents.add_argument("action", choices=["list"])
    policy = commands.add_parser("policy")
    policy.add_argument("action", choices=["check", "explain"])
    policy.add_argument("rule_id", nargs="?")
    policy.add_argument("--task-type", default="experiment_design")
    pdrw = commands.add_parser("pdrw", help="Bounded, read-only installed PD-RW-Agent inspection")
    pdrw.add_argument("action", choices=["inspect"])
    pdrw.add_argument("--project-id", required=True)
    pdrw.add_argument("--python", dest="pdrw_python", default=None,
                      help="Operator-selected Python executable where PD-RW-Agent RC is installed")
    schedule = commands.add_parser("schedule", help="Private scheduling intents only; never executes an Agent")
    schedule.add_argument("action", choices=["stage", "inspect", "mark-uncertain"])
    schedule.add_argument("--file", dest="plan_file")
    schedule.add_argument("--project-id")
    schedule.add_argument("--plan-id")
    schedule.add_argument("--task-id")
    schedule.add_argument("--attempt-id")
    schedule.add_argument("--with-pdrw", action="store_true", help="Opt-in read-only source recovery comparison")
    schedule.add_argument("--python", dest="pdrw_python", default=None)
    commands.add_parser("demo")
    return parser


def _schedule_action(args: argparse.Namespace) -> dict:
    if args.action == "stage":
        if not args.plan_file:
            raise ValueError("PLAN_FILE_REQUIRED")
        plan_id, tasks = _load_plan_file(args.plan_file)
        return stage_plan(plan_id, tasks)
    if not args.project_id or not args.plan_id:
        raise ValueError("PROJECT_ID_AND_PLAN_ID_REQUIRED")
    if args.action == "mark-uncertain":
        if not args.task_id or not args.attempt_id:
            raise ValueError("TASK_AND_ATTEMPT_IDS_REQUIRED")
        if args.with_pdrw:
            raise ValueError("WITH_PDRW_ONLY_FOR_INSPECTION")
        return mark_intent_uncertain(args.project_id, args.plan_id, args.task_id, args.attempt_id)
    local = inspect_plan(args.project_id, args.plan_id)
    if not args.with_pdrw:
        return local
    upstream = inspect_resume(args.project_id, python_executable=args.pdrw_python)
    return {"local": local, "upstream": upstream, "recovery": assess_recovery(local, upstream)}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "doctor":
            result = {"mode": "MOCK_EXECUTION_ONLY", "external_agents_ready": False,
                      "trusted_host_authorizer": False, "real_science_measured": False,
                      "pdrw": pdrw_status()}
        elif args.command == "agents":
            registry = load_agents(args.agents)
            result = [{"id": a.id, "capabilities": list(a.capabilities),
                       "configured_ready": a.ready,
                       "verified_ready": a.verified_ready} for a in registry]
        elif args.command == "policy":
            rules = load_policy(args.policy)
            if args.action == "check":
                result = {"status": "SHAPE_OK_ONLY", "rules": len(rules),
                          "author_grants_verified": False}
            else:
                matches = [r for r in rules if r.id == args.rule_id]
                if len(matches) != 1:
                    raise ValueError("rule_id not found or ambiguous")
                task = TaskPacket(task_id="EXPLAIN", project_id="EXAMPLE",
                                  task_type=args.task_type, objective="Explain applicability")
                guidance = compile_guidance(task, rules)
                result = {"rule": matches[0].__dict__,
                          "applies": matches[0].applies(task), "guidance": guidance.to_dict()}
        elif args.command == "pdrw":
            result = inspect_resume(args.project_id, python_executable=args.pdrw_python)
        elif args.command == "schedule":
            result = _schedule_action(args)
        elif args.command == "demo":
            report = run_demo(demo_plan(), load_agents(args.agents), load_policy(args.policy))
            result = report.to_dict()
        else:
            raise ValueError("command not implemented")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("bridge_status") in (None, "SOURCE_REVIEW_ONLY") else 3
    except (OSError, ValueError, TypeError, sqlite3.Error) as exc:
        print(json.dumps({"status": "ERROR", "reason": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
