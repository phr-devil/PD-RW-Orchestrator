"""Developer CLI; PD-RW read-only inspection and local operational plans only."""
from __future__ import annotations
import argparse
import json
import sqlite3
from pathlib import Path

from .agent_result import normalize_result
from .assets import data_root
from .adapters.codex import probe_codex
from .capabilities import accept_codex_pilot_probe
from .contracts import compile_pilot_contract, contract_sha256
from .host_evidence import inspect_pilot_receipt
from .runtime.codex_pilot import pilot_task
from .runtime.codex_pilot import run_codex_pilot
from .runtime.host_checks import audit_host, inspect_process
from .runtime.lifecycle import inspect_lifecycle
from .controller import run_demo
from .decision import decide_next
from .instruction import build_bundle
from .integrations.pdrw import inspect_resume, pdrw_status
from .integrations.source_checks import inspect_source_chain
from .planner import demo_plan
from .policy import load_policy, compile_guidance
from .models import TaskPacket
from .next_task import policy_task_for_proposal
from .registry import load_agents
from .runtime.store import (
    assess_recovery, inspect_plan, mark_intent_uncertain, stage_plan,
    _identifier, _store_path, has_exact_intent,
)


def _repository_root() -> Path:
    return data_root()


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


def _bounded_json_file(path: str, label: str) -> dict:
    source = Path(path)
    if not source.is_file() or source.stat().st_size > 128 * 1024:
        raise ValueError(f"{label}_FILE_MISSING_OR_TOO_LARGE")
    obj = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError(f"{label}_OBJECT_REQUIRED")
    return obj


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pdrw-orch", description="PD-RW operational orchestrator (opt-in synthetic Codex pilot)")
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
    pdrw.add_argument("action", choices=["inspect", "source-check"])
    pdrw.add_argument("--project-id", required=True)
    pdrw.add_argument("--operation-id", default=None)
    pdrw.add_argument("--run-id", default=None)
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
    codex = commands.add_parser("codex", help="Opt-in, synthetic-fixture-only Codex CLI pilot")
    codex.add_argument("action", choices=["probe", "contract", "inspect", "pilot"])
    codex.add_argument("--codex-bin", default=None, help="Operator-specified native Codex executable")
    codex.add_argument("--plan-id")
    codex.add_argument("--attempt-id")
    codex.add_argument("--execute", action="store_true",
                       help="Explicitly allow one real model subprocess for the synthetic fixture")
    codex.add_argument("--ack-external-model", action="store_true",
                       help="Acknowledge external model transmission and possible provider charges")
    host = commands.add_parser("host", help="Read-only local installation and process observations")
    host_actions = host.add_subparsers(dest="action", required=True)
    audit = host_actions.add_parser("audit", help="Inspect installed RC and original sources")
    audit.add_argument("--project-id", required=True)
    audit.add_argument("--task-id")
    audit.add_argument("--operation-id")
    audit.add_argument("--run-id")
    audit.add_argument("--python", dest="pdrw_python")
    audit.add_argument("--expected-version", default="1.0.0rc1")
    audit.add_argument("--expected-cli-sha256")
    process = host_actions.add_parser("process", help="Sample one operator-selected local PID")
    process.add_argument("--pid", type=int, required=True)
    process.add_argument("--expected-created-at", type=float)
    process.add_argument("--expected-exe-path-sha256")
    commands.add_parser("demo")
    advice = commands.add_parser("advise", help="Build an offline decision and ChatGPT handoff; no dispatch")
    advice.add_argument("--task-file", required=True)
    advice.add_argument("--result-file", required=True)
    advice.add_argument("--with-pdrw", action="store_true",
                        help="Use one read-only PD-RW-Agent resume, never grant permissions")
    advice.add_argument("--python", dest="pdrw_python", default=None)
    advice.add_argument("--source-operation-id", default=None)
    advice.add_argument("--source-run-id", default=None)
    advice.add_argument("--save", action="store_true",
                        help="Save handoff.json/md into private PDRW_ORCH_RUNTIME_DIR")
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
            result = {"mode": "EXTERNAL_CODEX_PILOT_OPT_IN_ONLY", "external_agents_ready": False,
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
            if args.action == "source-check":
                result = inspect_source_chain(
                    args.project_id, operation_id=args.operation_id,
                    run_id=args.run_id, python_executable=args.pdrw_python,
                )
            else:
                if args.operation_id or args.run_id:
                    raise ValueError("SOURCE_IDS_ONLY_VALID_WITH_SOURCE_CHECK")
                result = inspect_resume(args.project_id, python_executable=args.pdrw_python)
        elif args.command == "schedule":
            result = _schedule_action(args)
        elif args.command == "codex":
            if args.action != "pilot" and (args.execute or args.ack_external_model):
                raise ValueError("CODEX_READONLY_ACTION_REJECTS_EXECUTION_FLAGS")
            if args.action == "probe":
                if args.plan_id or args.attempt_id:
                    raise ValueError("CODEX_PROBE_DOES_NOT_ACCEPT_PLAN_IDS")
                probe = probe_codex(args.codex_bin)
                result = probe.to_dict()
                result["pilot_capability"] = accept_codex_pilot_probe(
                    probe, load_agents(args.agents), pilot_task()).to_dict()
            elif args.action == "contract":
                if args.plan_id or args.attempt_id:
                    raise ValueError("CONTRACT_PREVIEW_DOES_NOT_ACCEPT_PLAN_IDS")
                task = pilot_task()
                rules = load_policy(args.policy)
                contract = compile_pilot_contract(task, compile_guidance(task, rules))
                result = {
                    "status": "PILOT_CONTRACT_PREVIEW_ONLY",
                    "contract": contract,
                    "contract_sha256": contract_sha256(contract),
                    "model_invoked": False,
                    "execution_authorized": False,
                }
            elif args.action == "inspect":
                if args.codex_bin:
                    raise ValueError("INSPECT_DOES_NOT_INVOKE_CODEX")
                if not args.plan_id or not args.attempt_id:
                    raise ValueError("PLAN_AND_ATTEMPT_ID_REQUIRED")
                _identifier(args.plan_id, "plan_id")
                _identifier(args.attempt_id, "attempt_id")
                private_store = _store_path(create=False)
                if private_store is None or not private_store.is_file():
                    result = {"status": "NO_PLAN_STORE", "restart_permitted": False}
                elif not has_exact_intent("PILOT", args.plan_id, "CODEX-READ-001", args.attempt_id):
                    result = {"status": "PILOT_INTENT_NOT_FOUND", "restart_permitted": False}
                else:
                    run_dir = private_store.parent / "codex-pilot" / args.plan_id / args.attempt_id
                    result = inspect_pilot_receipt(
                        run_dir, project_id="PILOT", task_id="CODEX-READ-001",
                        attempt_id=args.attempt_id,
                    )
                    # Even after a crash with no final receipt, inspect the recorded lifecycle.
                    contract_file = run_dir / "task-contract.json"
                    if contract_file.is_file() and not contract_file.is_symlink() and contract_file.stat().st_size <= 12288:
                        import hashlib
                        digest = hashlib.sha256(contract_file.read_bytes()).hexdigest()
                        result["process_lifecycle"] = inspect_lifecycle(
                            run_dir, plan_id=args.plan_id, attempt_id=args.attempt_id,
                            contract_sha256=digest,
                        )
            else:
                if not (args.execute and args.ack_external_model):
                    raise ValueError("EXPLICIT_MODEL_OPT_IN_REQUIRED")
                if not args.plan_id or not args.attempt_id:
                    raise ValueError("PLAN_AND_ATTEMPT_ID_REQUIRED")
                result = run_codex_pilot(
                    plan_id=args.plan_id, attempt_id=args.attempt_id,
                    codex_bin=args.codex_bin,
                    policy_path=args.policy, registry_path=args.agents,
                )
        elif args.command == "host":
            if args.action == "audit":
                result = audit_host(
                    args.project_id, task_id=args.task_id, operation_id=args.operation_id,
                    run_id=args.run_id, python_executable=args.pdrw_python,
                    expected_version=args.expected_version,
                    expected_cli_sha256=args.expected_cli_sha256,
                )
            else:
                result = inspect_process(
                    args.pid, expected_created_at=args.expected_created_at,
                    expected_exe_path_sha256=args.expected_exe_path_sha256,
                )
        elif args.command == "demo":
            report = run_demo(demo_plan(), load_agents(args.agents), load_policy(args.policy))
            result = report.to_dict()
        elif args.command == "advise":
            task = TaskPacket(**_bounded_json_file(args.task_file, "TASK"))
            original = _bounded_json_file(args.result_file, "RESULT")
            normalized = normalize_result(original, task)
            all_rules = load_policy(args.policy)
            guidance = compile_guidance(task, all_rules)
            if not args.with_pdrw and (args.source_operation_id or args.source_run_id):
                raise ValueError("SOURCE_IDS_REQUIRE_WITH_PDRW")
            if args.with_pdrw and (args.source_operation_id or args.source_run_id):
                original_check = inspect_source_chain(
                    task.project_id, operation_id=args.source_operation_id,
                    run_id=args.source_run_id, python_executable=args.pdrw_python,
                )
                source_ok = original_check["verification_status"] in (
                    "SOURCE_READ_ONLY_CHECKS_COMPLETE",
                    "SOURCE_RECONCILIATION_REQUIRED",
                )
                context = {
                    "bridge_status": "SOURCE_REVIEW_ONLY" if source_ok else "SOURCE_CHECK_UNAVAILABLE",
                    "project_id": original_check.get("project_id"),
                    "source_status": original_check.get("resume_status"),
                    "pending_scientific_review_count": original_check.get("pending_scientific_review_count", 0),
                    "unresolved_operation_count": original_check.get("unresolved_operation_count"),
                    "operational_reconciliation_required": original_check.get(
                        "operational_reconciliation_required"),
                    "source_chain_status": original_check["verification_status"],
                    "source_chain": original_check,
                    "authorization_verified": False,
                    "project_identity_authenticated": False,
                    "scientific_completion_verified": False,
                }
                for checked in (original_check.get("operation"), original_check.get("run")):
                    if checked is not None and checked.get("task_id_declared") != task.task_id:
                        context["source_chain_status"] = "SOURCE_TASK_IDENTITY_MISMATCH"
                        break
            else:
                context = inspect_resume(
                    task.project_id, python_executable=args.pdrw_python,
                ) if args.with_pdrw else None
            decision = decide_next(task, normalized, guidance, load_agents(args.agents), source_context=context)
            next_guidance = compile_guidance(policy_task_for_proposal(decision["next_task"]), all_rules)
            result = build_bundle(task, normalized, decision, guidance,
                                  next_guidance=next_guidance, source_context=context)
            if args.save:
                from .instruction import save_bundle
                result["saved_files"] = save_bundle(result)
        else:
            raise ValueError("command not implemented")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if args.command == "codex":
            return 0 if result.get("status") in (
                "CLI_CAPABILITY_PROBE_OK", "PILOT_CONTRACT_PREVIEW_ONLY",
                "LOCAL_BYTES_MATCH_NOT_SCIENCE", "LOCAL_RECEIPT_MATCH_NO_OUTPUT",
                "STRUCTURED_OUTPUT_RECEIVED",
            ) else 3
        if args.command == "host":
            return 0 if result["status"] in (
                "HOST_READ_ONLY_CHECKS_COMPLETE", "PROCESS_OBSERVED_UNBOUND",
                "PROCESS_MATCH_ALIVE",
            ) else 3
        if args.command == "pdrw" and args.action == "source-check":
            return 0 if result["verification_status"] == "SOURCE_READ_ONLY_CHECKS_COMPLETE" else 3
        return 0 if (not isinstance(result, dict) or
                     result.get("bridge_status") in (None, "SOURCE_REVIEW_ONLY")) else 3
    except (OSError, ValueError, TypeError, sqlite3.Error) as exc:
        print(json.dumps({"status": "ERROR", "reason": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
