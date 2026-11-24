"""Compact proposed next-task instructions and ChatGPT handoff; draft-only."""
from __future__ import annotations
import json
from typing import Any
from .models import TaskPacket
from .policy import GuidancePacket

def _literal(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)

def _policy_lines(packet: GuidancePacket | None) -> list[str]:
    if packet is None:
        return ["- NOT_COMPILED_FOR_PROPOSED_TASK"]
    lines = []
    for item in packet.selected_items[:8]:
        level = "ADVISORY_UNVERIFIED" if item["level"] == "experience" else item["level"].upper()
        line = "- " + item["id"] + " [" + level + ", " + item["applicability"] + "] " + _literal(item["text"])
        if item["level"] == "experience":
            line += " | conditions (unverified): " + _literal(item["conditions"]) + " | evidence: " + _literal(item["evidence_refs"]) + " | source: " + _literal(item["source"])
        lines.append(line)
    return lines or ["- No matching guidance; original PD-RW remains authoritative"]

def build_instruction(task: TaskPacket, normalized: dict[str, Any],
                      decision: dict, guidance: GuidancePacket, *,
                      next_guidance: GuidancePacket | None = None) -> str:
    proposal = decision["next_task"]
    lines = [
        "# DRAFT NEXT Task Contract — NOT AUTHORIZATION",
        "Project: " + _literal(proposal["project_id"]),
        "Previous task (historical only): " + _literal(task.task_id),
        "Previous objective (NOT current instruction): " + _literal(task.objective),
        "NEW task objective: " + _literal(proposal["objective"]),
        "NEW task type / capability: " + _literal([proposal["task_type"], proposal["capability"]]),
        "Proposed agent (only after real adapter verification): " + _literal(decision["recommended_agent_id"]),
        "Decision: " + decision["decision_type"],
        "Original protocol refs (not reverified): " + _literal(proposal["original_protocol_refs"]),
        "Original evidence refs (not reverified): " + _literal(proposal["original_evidence_refs"]),
        "UNTRUSTED prior Agent artifact refs: " + _literal(proposal["unverified_agent_artifact_refs"]),
        "Prior grant refs (not transferred or authenticated): " +
        _literal(proposal["prior_authorization_refs_unverified"]),
        "Prior requested effects (scope review only, NOT inherited): " +
        _literal(proposal["prior_effects_for_scope_review_only"]),
        "Next-task requested effects: " + _literal(proposal["required_effects"]),
        "Next-task budget (NOT inherited): " + _literal(proposal["budget"]),
        "Applicable guidance FOR THE NEW TASK (not automatic permission):",
        *_policy_lines(next_guidance),
        "Previous Agent self-report status (UNTRUSTED_AGENT_OUTPUT): " +
        _literal(normalized["execution"]["reported_status"]),
        "Agent findings are quoted as untrusted source data: " +
        _literal([f["claim"] for f in normalized["findings"][:8]]),
        "Acceptance criteria: " + _literal(proposal["acceptance_criteria"]),
        "Stop conditions: " + _literal(proposal["stop_conditions"]),
        "Boundaries: verify original scientific evidence and existing author scope. "
        "No SEALED/VAL/CONFIRMATION access, new downloads, training, manuscripts or submissions "
        "without original permission. Never turn Agent claims or distilled advice into rules.",
        "NOT DISPATCHABLE: host authorization and actual specialist adapter are not connected.",
    ]
    return "\n".join(lines) + "\n"

def build_chatgpt_report(task: TaskPacket, normalized: dict[str, Any],
                         decision: dict, guidance: GuidancePacket, *,
                         next_guidance: GuidancePacket | None = None) -> str:
    proposal = decision["next_task"]
    lines = [
        "# ChatGPT Handoff Report (candidate; original evidence not verified)",
        "",
        "## 1. Original research task",
        _literal({"project": task.project_id, "task": task.task_id, "objective": task.objective}),
        "",
        "## 2. Work reported by previous Agent",
        _literal({"agent": normalized["agent_id"], "reported_execution": normalized["execution"]["reported_status"],
                  "artifact_refs_unverified": normalized["deliverables"]}),
        "",
        "## 3. Scientific assessment",
        "Effective science: NOT_ASSESSED; original protocol and artifact evidence require independent verification.",
        "Reported scientific outcome (unverified): " + _literal(normalized["scientific_assessment"].get("reported_outcome", "NOT_ASSESSED")),
        "Untrusted findings: " + _literal(normalized["findings"][:8]),
        "Warning codes: " + _literal(normalized["warning_codes"]),
        "",
        "## 4. Gaps and blockers",
        "Unresolved issues reported: " + _literal(normalized["unresolved_issues"][:8]),
        "Authorization: " + decision["authorization_status"],
        "",
        "## 5. Recommended next action (ADVISORY ONLY)",
        "Decision: " + decision["decision_type"] + "; reasons: " + _literal(decision["reason_codes"]),
        "NEXT objective: " + _literal(proposal["objective"]),
        "NEXT task type: " + _literal(proposal["task_type"]) + "; capability: " + _literal(proposal["capability"]),
        "Verified Agent: " + _literal(decision["recommended_agent_id"]),
        "No next-task dispatch occurred. Previous execution facts, if available, are in the host receipt.",
        "",
        "## 6. Next ChatGPT instruction inputs",
        "Next-task acceptance: " + _literal(proposal["acceptance_criteria"]),
        "Next-task stop conditions: " + _literal(proposal["stop_conditions"]),
        "Next-task guidance IDs: " + _literal(list(next_guidance.rule_ids) if next_guidance else []),
        "Protocol refs: " + _literal(proposal["original_protocol_refs"]),
        "Original evidence refs: " + _literal(proposal["original_evidence_refs"]),
        "Agent artifact refs (unverified): " + _literal(proposal["unverified_agent_artifact_refs"]),
        "ChatGPT should check original source and author scope before forming any new executable instruction.",
        "",
    ]
    return "\n".join(lines)

def build_bundle(task: TaskPacket, normalized: dict[str, Any],
                 decision: dict, guidance: GuidancePacket, *,
                 next_guidance: GuidancePacket | None = None,
                 source_context: dict | None = None,
                 previous_execution: dict[str, Any] | None = None,
                 host_artifact_review: dict[str, Any] | None = None) -> dict:
    return {
        "schema_version": "1.1", "mode": "ADVISORY_DRAFT_ONLY",
        "project_id": task.project_id, "task_id": task.task_id,
        "result": normalized, "decision": decision,
        "next_task": decision["next_task"],
        "guidance": guidance.to_dict(),  # previous-task guidance kept for compatible readers
        "next_guidance": (next_guidance.to_dict() if next_guidance is not None
                          else {"status": "NOT_COMPILED_FOR_NEXT_TASK"}),
        "source_context": source_context,
        "previous_execution": previous_execution if previous_execution is not None else {
            "origin": "NOT_CONNECTED_TO_HOST", "dispatch_attempted": False,
            "external_model_usage_verified": False, "scientific_completion_verified": False,
        },
        "next_dispatch_performed": False,
        "dispatch_scope": "NEXT_TASK_ONLY",
        "host_artifact_review": host_artifact_review if host_artifact_review is not None else {
            "status": "NOT_CHECKED",
            "original_pd_rw_evidence_verified": False,
            "authorization_verified": False,
            "scientific_completion_verified": False,
        },
        "agent_instruction_draft": build_instruction(
            task, normalized, decision, guidance, next_guidance=next_guidance),
        "chatgpt_handoff_md": build_chatgpt_report(
            task, normalized, decision, guidance, next_guidance=next_guidance),
        "dispatch_performed": False, "authorization_verified": False,
        "scientific_completion_verified": False,
    }

def save_bundle(bundle: dict) -> dict[str, str]:
    """Atomically export a private, content-verified *draft* handoff.

    Only operational report copies are stored. Existing outputs are checked
    against their *actual bytes*, including Markdown, not just the manifest.
    """
    import hashlib
    import os
    import re
    import shutil
    import tempfile
    from pathlib import Path
    from .runtime.store import _store_path

    project_id = bundle["project_id"]
    task_id = bundle["task_id"]
    safe = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}\Z")
    if not safe.fullmatch(project_id) or not safe.fullmatch(task_id):
        raise ValueError("EXPORT_ID_INVALID")
    json_body = (json.dumps(bundle, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    markdown_body = bundle["chatgpt_handoff_md"].encode("utf-8")
    json_hash = hashlib.sha256(json_body).hexdigest()
    md_hash = hashlib.sha256(markdown_body).hexdigest()
    db_path = _store_path(create=True)
    assert db_path is not None
    export_root = db_path.parent / "handoffs"
    if export_root.is_symlink():
        raise ValueError("HANDOFF_EXPORT_ROOT_SYMLINK")
    export_root.mkdir(mode=0o700, exist_ok=True)
    destination = export_root / (project_id + "." + task_id + "." + json_hash[:20])
    expected = {"handoff.json": json_body, "handoff.md": markdown_body}
    def check_existing() -> dict[str, str]:
        if destination.is_symlink() or not destination.is_dir():
            raise ValueError("HANDOFF_EXPORT_PATH_INVALID")
        manifest = destination / "COMPLETE.json"
        if manifest.is_symlink() or not manifest.is_file():
            raise ValueError("PARTIAL_HANDOFF_EXPORT_REQUIRES_MANUAL_RECONCILIATION")
        record = json.loads(manifest.read_text(encoding="utf-8"))
        if record.get("sha256") != json_hash:
            raise ValueError("HANDOFF_HASH_MISMATCH")
        if record.get("markdown_sha256", md_hash) != md_hash:
            raise ValueError("HANDOFF_MARKDOWN_HASH_MISMATCH")
        for name, body in expected.items():
            file = destination / name
            if file.is_symlink() or not file.is_file() or file.read_bytes() != body:
                raise ValueError("HANDOFF_CONTENT_MISMATCH")
        return {"handoff_json": str(destination / "handoff.json"),
                "handoff_md": str(destination / "handoff.md"),
                "status": "ALREADY_EXPORTED"}
    if destination.exists() or destination.is_symlink():
        return check_existing()
    tmp = Path(tempfile.mkdtemp(prefix=".staging-", dir=export_root))
    try:
        for name, body in expected.items():
            (tmp / name).write_bytes(body)
        (tmp / "COMPLETE.json").write_text(json.dumps({
            "sha256": json_hash, "markdown_sha256": md_hash,
            "status": "COMPLETE_DRAFT_ONLY"
        }), encoding="utf-8")
        try:
            os.rename(tmp, destination)
        except OSError:
            if destination.exists() or destination.is_symlink():
                return check_existing()
            raise
    finally:
        if tmp.exists():
            shutil.rmtree(tmp)
    return {"handoff_json": str(destination / "handoff.json"),
            "handoff_md": str(destination / "handoff.md"),
            "status": "EXPORTED_DRAFT_ONLY"}
