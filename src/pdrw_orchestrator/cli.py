"""Developer CLI; only PD-RW-Agent read-only inspection is a real integration."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

from .controller import run_demo
from .integrations.pdrw import inspect_resume, pdrw_status
from .planner import demo_plan
from .policy import load_policy, compile_guidance
from .models import TaskPacket
from .registry import load_agents


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


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
    commands.add_parser("demo")
    return parser


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
        elif args.command == "demo":
            report = run_demo(demo_plan(), load_agents(args.agents), load_policy(args.policy))
            result = report.to_dict()
        else:
            raise ValueError("command not implemented")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("bridge_status") in (None, "SOURCE_REVIEW_ONLY") else 3
    except (OSError, ValueError, TypeError) as exc:
        print(json.dumps({"status": "ERROR", "reason": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
