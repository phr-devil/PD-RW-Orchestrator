"""Opt-in Codex pilot orchestration, synthetic-only; no project execution.

One attempt is reserved in the existing private SQLite intent store BEFORE any
external subprocess. Unknown attempts remain unresolved; no implicit retries.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from pdrw_orchestrator.adapters.codex import (
    probe_codex, run_readonly_pilot, verify_fixture,
)
from pdrw_orchestrator.agent_result import normalize_result
from pdrw_orchestrator.decision import decide_next
from pdrw_orchestrator.instruction import build_bundle, save_bundle
from pdrw_orchestrator.models import TaskPacket
from pdrw_orchestrator.next_task import policy_task_for_proposal
from pdrw_orchestrator.policy import compile_guidance, load_policy
from pdrw_orchestrator.registry import load_agents
from pdrw_orchestrator.runtime.store import (
    _store_path, mark_intent_uncertain, stage_plan,
)

PILOT_PROJECT_ID = "PILOT"
PILOT_TASK_ID = "CODEX-READ-001"


def pilot_task() -> TaskPacket:
    return TaskPacket(
        project_id=PILOT_PROJECT_ID,
        task_id=PILOT_TASK_ID,
        task_type="review",
        capability="review",
        objective=(
            "Read only the public synthetic sensor fixture; identify potential "
            "evaluation issues and propose independent checks. No scientific "
            "claims, no training or code modification."
        ),
        required_effects=(),
        evidence_refs=(),
        protocol_refs=(),
        authorization_refs=(),
        idempotency_key="PILOT-CODEX-READ-001",
        budget={"max_attempts": 1, "max_wall_seconds": 120},
    )


def _readout_to_result(
    invocation: dict, task: TaskPacket, attempt_id: str, report_path: Path,
) -> dict:
    status = invocation["status"]
    report = invocation.get("report")
    success = status == "STRUCTURED_OUTPUT_RECEIVED" and isinstance(report, dict)
    if success:
        raw_status = "COMPLETED"
    elif status in ("TIMEOUT_PROCESS_STATE_UNCERTAIN", "PROCESS_LAUNCH_FAILED_UNCERTAIN",
                    "NO_MACHINE_READABLE_OUTPUT", "OUTPUT_EXCEEDS_LIMIT",
                    "INVALID_MACHINE_READABLE_OUTPUT"):
        raw_status = "BLOCKED_DEPENDENCY"
    else:
        raw_status = "FAILED"
    findings = []
    if success:
        for observation in report["observations"]:
            findings.append({
                "claim": observation["claim"],
                "source_refs": observation["source_refs"],
                "limitations": observation["limitations"],
            })
    return {
        "schema_version": "2.0", "project_id": task.project_id,
        "task_id": task.task_id, "agent_id": "codex-local",
        "attempt_id": attempt_id,
        "execution": {"status": raw_status, "budget_exhausted": status == "TIMEOUT_PROCESS_STATE_UNCERTAIN"},
        "deliverables": {
            "report_refs": [str(report_path)] if success else [],
        },
        "findings": findings,
        "scientific_assessment": {
            "claim_status": "NOT_ASSESSED", "protocol_status": "NOT_ASSESSED",
            "review_required": True,
        },
        "unresolved_issues": ([status] if not success else list(report["limitations"])),
        "next_action_candidates": (report["next_actions"] if success else []),
        "authorization_verified": False, "scientific_completion_verified": False,
    }


def run_codex_pilot(
    *, plan_id: str, attempt_id: str, codex_bin: str | None,
    policy_path: str | Path, registry_path: str | Path,
) -> dict:
    """Actual model invocation: caller must enforce explicit opt-in separately."""
    verify_fixture()
    probe = probe_codex(codex_bin)
    if not probe.supported or not probe.executable:
        return {"status": "NOT_CONNECTED", "probe": probe.to_dict(),
                "model_invoked": False}
    task = pilot_task()
    # This is intentionally the only possible task; it has zero project effects.
    stage = stage_plan(plan_id, (task,))
    intent = mark_intent_uncertain(task.project_id, plan_id, task.task_id, attempt_id)
    if intent["status"] != "INTENT_UNCERTAIN_NO_DISPATCH":
        return {"status": "ALREADY_RESERVED_NO_RETRY", "model_invoked": False,
                "plan_id": plan_id, "attempt_id": attempt_id}

    db_path = _store_path(create=False)
    assert db_path is not None
    run_dir = db_path.parent / "codex-pilot" / plan_id / attempt_id
    if run_dir.exists() or run_dir.is_symlink():
        raise ValueError("PILOT_ATTEMPT_ARTIFACT_COLLISION_NO_RETRY")
    run_dir.mkdir(parents=True)
    output_path = run_dir / "codex-final.json"
    try:
        invocation = run_readonly_pilot(
            executable=probe.executable,
            output_path=output_path,
            wall_seconds=task.budget["max_wall_seconds"],
        )
        payload = _readout_to_result(invocation, task, attempt_id, output_path)
        normalized = normalize_result(payload, task)
        rules = load_policy(policy_path)
        guidance = compile_guidance(task, rules)
        decision = decide_next(task, normalized, guidance, load_agents(registry_path))
        next_guidance = compile_guidance(policy_task_for_proposal(decision["next_task"]), rules)
        bundle = build_bundle(task, normalized, decision, guidance,
                              next_guidance=next_guidance)
        saved = save_bundle(bundle)
        return {
            "status": invocation["status"],
            "mode": "EXTERNAL_CODEX_READONLY_SYNTHETIC_PILOT",
            "model_invocation_attempted": True,
            "model_invoked_confirmed": invocation["status"] == "STRUCTURED_OUTPUT_RECEIVED",
            "project_id": task.project_id,
            "plan_id": plan_id,
            "attempt_id": attempt_id,
            "codex_version_probed": probe.version,
            "process_returncode": invocation.get("returncode"),
            "structured_output_sha256": (
                hashlib.sha256(output_path.read_bytes()).hexdigest()
                if output_path.is_file() else None
            ),
            "private_report": saved,
            "decision_type": decision["decision_type"],
            "next_task": decision["next_task"],
            "execution_authorized_for_research": False,
            "science_validated": False,
            "restart_permitted": False,
        }
    except Exception:
        # The state was intentionally reserved first. Never allow a new attempt
        # merely because the process failed to return a usable result.
        raise
