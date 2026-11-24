"""R2-B: scoped read-only verification against original PD-RW-Agent RC sources.

SOURCE reports are never execution grants, independent science acceptance,
proof of process liveness, or host identity authentication. This module does
not read research files directly and never makes write-enabled CLI calls.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Mapping

from .pdrw import inspect_resume

_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}\Z")
_MAX_CONFIG = 128 * 1024
_MAX_REPLY = 256 * 1024
_STATUS_OK = {"RECEIPTS_FOUND", "NO_RECEIPTS", "RECEIPTS_NOT_CONFIGURED"}
_RUN_BYTE_MATCHED = {"RUN_BYTES_MATCHED_ONLY", "RUN_SOURCE_MATCHED_ONLY"}
_OP_RECOVERY = {
    "VERIFY_ACTUAL_EXECUTION", "PENDING_SCIENTIFIC_REVIEW",
    "NEEDS_ARTIFACT_RECONCILIATION", "REVIEW_TECHNICAL_FAILURE",
}
_PROTECTED = ("sealed", "holdout", "confirmation")


def _result(project_id: str, status: str, **extra) -> dict:
    return {
        "schema_version": "1.0",
        "project_id": project_id,
        "verification_status": status,
        "source_authority": "ORIGINAL_PD_RW_AGENT_CLI_READ_ONLY_REPORT",
        "project_identity_authenticated": False,
        "author_scope_verified": False,
        "execution_authorized": False,
        "process_liveness_verified": False,
        "scientific_validity_verified": False,
        "restart_permitted": False,
        "raw_project_content_returned": False,
        **extra,
    }


def _source_settings(project_id: str, env: dict) -> tuple[dict, str | None]:
    """Validate project registry existence, not its scientific identity."""
    location = env.get("PDRW_AGENT_CONFIG")
    workflow = env.get("PDRW_WORKFLOW_ROOT")
    if not location or not workflow:
        return {}, "PDRW_NOT_CONFIGURED"
    try:
        config_path = Path(location).expanduser().resolve()
        workflow_root = Path(workflow).expanduser().resolve()
        if (not config_path.is_file() or config_path.stat().st_size > _MAX_CONFIG
                or not (workflow_root / "AGENTS.md").is_file()
                or not (workflow_root / "WORKFLOW.md").is_file()):
            return {}, "SOURCE_CONFIG_UNAVAILABLE"
        with config_path.open("rb") as stream:
            raw = stream.read(_MAX_CONFIG + 1)
        if len(raw) > _MAX_CONFIG:
            return {}, "SOURCE_CONFIG_UNAVAILABLE"
        # Sample exact rule bytes alongside the private mapping. A later
        # fingerprint mismatch blocks mixed-version multi-call results.
        workflow_bytes = []
        for name in ("AGENTS.md", "WORKFLOW.md"):
            file = workflow_root / name
            if file.stat().st_size > 2 * 1024 * 1024:
                return {}, "SOURCE_RULE_FILE_OVERSIZE"
            with file.open("rb") as stream:
                data = stream.read(2 * 1024 * 1024 + 1)
            if len(data) > 2 * 1024 * 1024:
                return {}, "SOURCE_RULE_FILE_OVERSIZE"
            workflow_bytes.append(data)
        registry = json.loads(raw.decode("utf-8-sig"))
        if (not isinstance(registry, dict)
                or registry.get("schema_version") != 1
                or not isinstance(registry.get("projects"), dict)):
            return {}, "SOURCE_REGISTRY_CONTRACT_INVALID"
        item = registry["projects"].get(project_id)
        if not isinstance(item, dict) or not isinstance(item.get("root"), str):
            return {}, "SOURCE_PROJECT_NOT_REGISTERED"
        if not Path(item["root"]).expanduser().resolve().is_dir():
            return {}, "SOURCE_PROJECT_ROOT_MISSING"
        return {
            "registry_sha256_local_only": hashlib.sha256(raw).hexdigest(),
            "rule_files_sha256_local_only": hashlib.sha256(
                b"AGENTS.md\x00" + workflow_bytes[0] +
                b"\x00WORKFLOW.md\x00" + workflow_bytes[1]
            ).hexdigest(),
        }, None
    except (OSError, UnicodeError, ValueError, TypeError):
        return {}, "SOURCE_CONFIG_UNREADABLE"


def _read_cli(
    *, project_id: str, command: str, identifier: str,
    python_executable: str, env: dict, timeout_seconds: int,
) -> tuple[dict | None, str | None]:
    """Read no more than MAX_REPLY into Python memory; discard stderr.

    The temporary OS-owned file avoids capture_output buffering potentially
    arbitrarily large original source material in process memory. The time
    limit bounds the subprocess; CLI output is never returned verbatim.
    """
    if command not in ("operations", "verify-run"):
        return None, "SOURCE_COMMAND_NOT_ALLOWED"
    if command == "operations":
        argv = [str(Path(python_executable).absolute()), "-I", "-B", "-m", "pdrw_agent.cli", "operations",
                "--project-id", project_id, "--operation-id", identifier, "--limit", "1"]
    else:
        argv = [str(Path(python_executable).absolute()), "-I", "-B", "-m", "pdrw_agent.cli", "verify-run",
                "--project-id", project_id, "--run-id", identifier]
    try:
        with tempfile.TemporaryFile(mode="w+b") as sink:
            finished = subprocess.run(
                argv, stdout=sink, stderr=subprocess.DEVNULL,
                timeout=timeout_seconds, check=False, env=env,
            )
            sink.seek(0)
            body = sink.read(_MAX_REPLY + 1)
            if len(body) > _MAX_REPLY:
                return None, "SOURCE_OUTPUT_TOO_LARGE"
    except subprocess.TimeoutExpired:
        return None, "SOURCE_TIMEOUT_NO_RETRY"
    except OSError:
        return None, "SOURCE_PROCESS_UNAVAILABLE"
    try:
        payload = json.loads(body.decode("utf-8-sig"))
    except (UnicodeError, ValueError):
        return None, "SOURCE_JSON_INVALID"
    if not isinstance(payload, dict) or not isinstance(payload.get("status"), str):
        return None, "SOURCE_CONTRACT_INVALID"
    if finished.returncode != 0 or payload["status"] == "ERROR":
        return None, "SOURCE_UPSTREAM_ERROR"
    return payload, None


def _operation_check(payload: dict, project_id: str, operation_id: str) -> dict:
    status = payload["status"]
    if status not in _STATUS_OK:
        return {"status": "OPERATION_STATUS_UNKNOWN", "reconciliation_required": True}
    ops = payload.get("operations")
    if not isinstance(ops, list):
        return {"status": "OPERATION_CONTRACT_INVALID", "reconciliation_required": True}
    if bool(ops) != (status == "RECEIPTS_FOUND"):
        return {"status": "OPERATION_STATUS_ROWS_CONFLICT", "reconciliation_required": True}
    if not ops:
        return {"status": "OPERATION_NOT_FOUND_UNKNOWN", "reconciliation_required": True}
    if len(ops) != 1 or not isinstance(ops[0], dict):
        return {"status": "OPERATION_ID_CONFLICT", "reconciliation_required": True}
    row = ops[0]
    if (row.get("project_id") != project_id
            or row.get("operation_id") != operation_id):
        return {"status": "OPERATION_IDENTITY_MISMATCH", "reconciliation_required": True}
    recovery = row.get("recovery_class")
    integrity = row.get("artifact_integrity")
    task = row.get("task_id")
    phase = row.get("phase")
    expected_recovery = {
        "PLANNED": "VERIFY_ACTUAL_EXECUTION",
        "RUNNING_DECLARED": "VERIFY_ACTUAL_EXECUTION",
        "TECHNICAL_FAILED": "REVIEW_TECHNICAL_FAILURE",
    }
    if (not isinstance(task, str) or not _ID.fullmatch(task)
            or not isinstance(recovery, str) or recovery not in _OP_RECOVERY
            or not isinstance(integrity, str) or integrity not in {"MATCH", "CHANGED", "MISSING_OR_UNAVAILABLE", "NOT_REPORTED"}
            or phase not in ("PLANNED", "RUNNING_DECLARED", "ARTIFACT_REPORTED",
                             "TECHNICAL_FAILED")
            or (phase in expected_recovery and recovery != expected_recovery[phase])
            or (phase == "ARTIFACT_REPORTED" and recovery != (
                "PENDING_SCIENTIFIC_REVIEW" if integrity == "MATCH" else "NEEDS_ARTIFACT_RECONCILIATION"))
            or (phase in ("PLANNED", "RUNNING_DECLARED") and integrity != "NOT_REPORTED")):
        return {"status": "OPERATION_FIELDS_INVALID", "reconciliation_required": True}
    # No textual receipt, path, note, or unrecognized original fields returned.
    return {
        "status": "SOURCE_OPERATION_REPORTED_ONLY",
        "operation_id": operation_id,
        "task_id_declared": task,
        "phase_declared": phase,
        "recovery_class": recovery,
        "artifact_integrity_reported": integrity,
        "process_liveness_verified": False,
        "original_science_registration_verified": False,
        "reconciliation_required": (
            recovery != "PENDING_SCIENTIFIC_REVIEW" or integrity != "MATCH"
        ),
    }


def _run_check(payload: dict, project_id: str, run_id: str) -> dict:
    status = payload["status"]
    if payload.get("project_id") != project_id or payload.get("run_id") != run_id:
        return {"status": "RUN_IDENTITY_MISMATCH", "reconciliation_required": True}
    if status not in _RUN_BYTE_MATCHED:
        # Preserve the controlled status, including PROTECTED_RUN_NOT_OPENED,
        # but never interpret UNKNOWN or INVALID as a negative result.
        safe = status if re.fullmatch(r"[A-Z][A-Z0-9_]{0,79}", status) else "RUN_STATUS_UNKNOWN"
        return {"status": safe, "reconciliation_required": True,
                "scientific_validity_verified": False}
    split = payload.get("split_declared")
    task = payload.get("task_id_declared")
    declared = payload.get("run_status_declared")
    protocol = payload.get("protocol_id_declared")
    if (split not in ("dev", "validation") or not isinstance(task, str)
            or not _ID.fullmatch(task)
            or not isinstance(protocol, str) or not _ID.fullmatch(protocol)
            or declared not in ("VALID", "INVALID", "INCONCLUSIVE", "NOT_RUN")
            or payload.get("original_contract_valid") is not True
            or payload.get("run_sha256_match") is not True):
        return {"status": "RUN_SOURCE_CONTRACT_INCOMPLETE", "reconciliation_required": True}
    if (status == "RUN_BYTES_MATCHED_ONLY" and declared != "VALID") or (
            status == "RUN_SOURCE_MATCHED_ONLY" and declared == "VALID"):
        return {"status": "RUN_SOURCE_STATUS_CONFLICT", "reconciliation_required": True}
    if status == "RUN_BYTES_MATCHED_ONLY" and payload.get(
            "linked_hash_coverage") != "ALL_DECLARED_REFERENCES_CHECKED":
        return {"status": "RUN_REFERENCES_NOT_CHECKED", "reconciliation_required": True}
    return {
        "status": status,
        "run_id": run_id,
        "task_id_declared": task,
        "split_declared": split,
        "protocol_id_declared": protocol,
        "run_status_declared": declared,
        "original_contract_valid": True,
        "run_source_file_consistent": True,
        "bytes_consistent": status == "RUN_BYTES_MATCHED_ONLY",
        "linked_artifacts_consistent": status == "RUN_BYTES_MATCHED_ONLY",
        "scientific_validity_verified": False,
        "reconciliation_required": False,
    }


def inspect_source_chain(
    project_id: str, *, operation_id: str | None = None,
    run_id: str | None = None, python_executable: str | None = None,
    environment: Mapping[str, str] | None = None,
    timeout_seconds: int = 30,
) -> dict:
    """Check original source identity/status + optional operation/Run metadata.

    No original authorization is granted, no SEALED accessed, and this cannot
    independently attest scientific claims or approve any old-job restart.
    """
    if not isinstance(project_id, str) or not _ID.fullmatch(project_id):
        return _result(str(project_id)[:80], "INVALID_PROJECT_ID")
    for key, val in (("OPERATION_ID", operation_id), ("RUN_ID", run_id)):
        if val is not None and (not isinstance(val, str) or not _ID.fullmatch(val)):
            return _result(project_id, "INVALID_" + key)
    if run_id and any(x in run_id.casefold() for x in _PROTECTED):
        return _result(project_id, "PROTECTED_RUN_IDENTIFIER_NOT_ALLOWED")
    if type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 90:
        return _result(project_id, "INVALID_TIMEOUT")
    env = dict(os.environ if environment is None else environment)
    config, error = _source_settings(project_id, env)
    if error:
        return _result(project_id, error)
    python = python_executable or sys.executable
    if not isinstance(python, str) or not Path(python).is_file():
        return _result(project_id, "SOURCE_PYTHON_NOT_FOUND")
    def source_snapshot_unchanged() -> bool:
        latest, check_error = _source_settings(project_id, env)
        return check_error is None and latest == config

    resume = inspect_resume(project_id, python_executable=python,
                            timeout_seconds=timeout_seconds, environment=env)
    if not source_snapshot_unchanged():
        return _result(project_id, "SOURCE_INPUT_CHANGED_DURING_CHECK")
    if resume.get("bridge_status") != "SOURCE_REVIEW_ONLY":
        return _result(project_id, "SOURCE_RESUME_UNAVAILABLE",
                       resume_status=resume.get("bridge_status"))
    if resume.get("project_id") != project_id:
        return _result(project_id, "SOURCE_PROJECT_ID_MISMATCH")
    source_status = resume.get("source_status")
    if not isinstance(source_status, str):
        return _result(project_id, "SOURCE_RESUME_STATUS_UNKNOWN")
    if source_status.startswith("BLOCKED_"):
        return _result(project_id, "SOURCE_PROJECT_BLOCKED",
                       resume_status=source_status,
                       active_task_id_declared=resume.get("active_task_id_declared"))
    if source_status not in {
            "SOURCE_REVIEW_REQUIRED", "ARTIFACT_REVIEW_PENDING",
            "NEEDS_RECONCILIATION", "NEEDS_OPERATIONAL_RECONCILIATION",
    }:
        return _result(project_id, "SOURCE_RESUME_STATUS_UNKNOWN")
    response = _result(
        project_id, "SOURCE_READ_ONLY_CHECKS_COMPLETE",
        registry_sha256_local_only=config["registry_sha256_local_only"],
        resume_status=source_status,
        scientific_resume_status=resume.get("scientific_resume_status"),
        checks_performed=["resume"],
        check_scope="ONLY_EXPLICITLY_REQUESTED_ORIGINAL_SOURCES",
        active_task_id_declared=resume.get("active_task_id_declared"),
        latest_valid_run_id_declared=resume.get("latest_valid_run_id_declared"),
        host_reconciliation_required_declared=resume.get("host_reconciliation_required_declared"),
        independent_permitted_read_only_review_hint=resume.get("independent_permitted_read_only_review_hint") is True,
        independent_review_authorization_verified=False,
        latest_rule_commit_local_only=resume.get("rule_commit_local_only"),
        rule_files_sha256_local_only=config["rule_files_sha256_local_only"],
        operational_reconciliation_required=bool(
            resume.get("operational_reconciliation_required")),
        unresolved_operation_count=resume.get("unresolved_operation_count"),
        pending_scientific_review_count=resume.get("pending_scientific_review_count", 0),
        operation=None, run=None,
    )
    for command, identifier in (("operations", operation_id), ("verify-run", run_id)):
        if identifier is None:
            continue
        response["checks_performed"].append(command)
        payload, error = _read_cli(
            project_id=project_id, command=command, identifier=identifier,
            python_executable=python, env=env, timeout_seconds=timeout_seconds,
        )
        if not source_snapshot_unchanged():
            return _result(project_id, "SOURCE_INPUT_CHANGED_DURING_CHECK")
        if error:
            response["verification_status"] = "SOURCE_RECONCILIATION_REQUIRED"
            response["source_error_code"] = error
            return response
        checked = (_operation_check(payload, project_id, identifier)
                   if command == "operations"
                   else _run_check(payload, project_id, identifier))
        response["operation" if command == "operations" else "run"] = checked
        if checked["reconciliation_required"]:
            response["verification_status"] = "SOURCE_RECONCILIATION_REQUIRED"
    if response["operation"] is not None and response["run"] is not None:
        op = response["operation"]
        run = response["run"]
        if not op.get("task_id_declared") or not run.get("task_id_declared"):
            response["verification_status"] = "SOURCE_RECONCILIATION_REQUIRED"
            response["cross_reference_status"] = "ORIGINAL_TASK_ID_UNKNOWN"
        elif op["task_id_declared"] != run["task_id_declared"]:
            response["verification_status"] = "SOURCE_RECONCILIATION_REQUIRED"
            response["cross_reference_status"] = "ORIGINAL_TASK_ID_MISMATCH"
        else:
            response["cross_reference_status"] = "TASK_ID_DECLARATIONS_MATCH_ONLY"
    if (source_status in ("NEEDS_RECONCILIATION", "NEEDS_OPERATIONAL_RECONCILIATION")
            or response["operational_reconciliation_required"]
            or response["unresolved_operation_count"]):
        response["verification_status"] = "SOURCE_RECONCILIATION_REQUIRED"
    # No execution/science/permission positive state in this function.
    return response
