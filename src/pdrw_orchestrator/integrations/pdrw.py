"""Bounded read-only bridge to the installed PD-RW-Agent CLI.

Only the upstream 'resume' command is called. Output is *source-reported*
context, not identity verification, permission or scientific acceptance.
No model-supplied executable, shell interpolation or raw evidence is returned.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from importlib.util import find_spec
from pathlib import Path
from typing import Mapping

_PROJECT_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}\Z")
_MAX_STDOUT_BYTES = 256 * 1024


def pdrw_status() -> dict:
    installed = find_spec("pdrw_agent") is not None
    configured = bool(os.getenv("PDRW_AGENT_CONFIG") and os.getenv("PDRW_WORKFLOW_ROOT"))
    return {
        "component": "PD-RW-Agent",
        "python_package_importable": installed,
        "local_source_config_present": configured,
        "mcp_connected": False,
        "project_identity_authenticated": False,
        "host_permission_verified": False,
        "status": "ADAPTER_NOT_CONNECTED",
    }


def _blocked(code: str, project_id: str, **extra: object) -> dict:
    return {
        "bridge_status": code,
        "project_id": project_id,
        "authorization_verified": False,
        "project_identity_authenticated": False,
        "execution_authorized": False,
        "restart_permitted": False,
        "scientific_completion_verified": False,
        **extra,
    }


def inspect_resume(
    project_id: str,
    *,
    python_executable: str | None = None,
    timeout_seconds: int = 30,
    environment: Mapping[str, str] | None = None,
) -> dict:
    """Read a locally mapped project once through PD-RW-Agent's actual CLI.

    An operator controls the executable and environment, not the task model.
    This never asserts that the original user authorized an execution.
    """
    if not isinstance(project_id, str) or not _PROJECT_ID.fullmatch(project_id):
        return _blocked("INVALID_PROJECT_ID", str(project_id)[:80])
    if type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 90:
        return _blocked("INVALID_TIMEOUT", project_id)
    env = dict(os.environ if environment is None else environment)
    config_path = env.get("PDRW_AGENT_CONFIG", "")
    rules_path = env.get("PDRW_WORKFLOW_ROOT", "")
    if not config_path or not rules_path:
        return _blocked("PDRW_NOT_CONFIGURED", project_id)
    try:
        if not Path(config_path).is_file():
            return _blocked("PROJECT_MAP_MISSING", project_id)
        root = Path(rules_path)
        if not (root / "AGENTS.md").is_file() or not (root / "WORKFLOW.md").is_file():
            return _blocked("WORKFLOW_ROOT_INVALID", project_id)
    except OSError:
        return _blocked("LOCAL_CONFIG_UNREADABLE", project_id)
    executable = python_executable or sys.executable
    if not isinstance(executable, str) or not executable or not Path(executable).is_file():
        return _blocked("PYTHON_EXECUTABLE_UNAVAILABLE", project_id)

    argv = [executable, "-m", "pdrw_agent.cli", "resume", "--project-id", project_id]
    try:
        completed = subprocess.run(
            argv, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=timeout_seconds, check=False, env=env,
        )
    except subprocess.TimeoutExpired:
        return _blocked("UPSTREAM_TIMEOUT_NO_RETRY", project_id)
    except OSError:
        return _blocked("UPSTREAM_PROCESS_UNAVAILABLE", project_id)
    output = completed.stdout
    if len(output.encode("utf-8")) > _MAX_STDOUT_BYTES:
        return _blocked("UPSTREAM_OUTPUT_TOO_LARGE", project_id)
    try:
        payload = json.loads(output)
    except (TypeError, ValueError):
        return _blocked("UPSTREAM_INVALID_JSON", project_id, upstream_returncode=completed.returncode)
    if not isinstance(payload, dict) or not isinstance(payload.get("status"), str):
        return _blocked("UPSTREAM_INVALID_CONTRACT", project_id)
    if payload.get("status") == "ERROR" or completed.returncode != 0:
        return _blocked(
            "UPSTREAM_ERROR", project_id, upstream_returncode=completed.returncode,
            upstream_error_code=payload.get("error_code", "UNKNOWN"),
        )
    if payload.get("project_id") != project_id:
        return _blocked("UPSTREAM_PROJECT_ID_MISMATCH", project_id)
    scientific = payload.get("scientific_context") or {}
    operations = payload.get("operation_context") or {}
    next_hint = payload.get("next_action_hint") or {}
    if not all(isinstance(v, dict) for v in (scientific, operations, next_hint)):
        return _blocked("UPSTREAM_INVALID_CONTEXT", project_id)
    declared = scientific.get("active_task_id_declared")
    unresolved = operations.get("unresolved", [])
    if not isinstance(unresolved, list):
        return _blocked("UPSTREAM_INVALID_OPERATIONS", project_id)
    return {
        "bridge_status": "SOURCE_REVIEW_ONLY",
        "project_id": project_id,
        "source_status": payload["status"],
        "scientific_resume_status": payload.get("scientific_resume_status"),
        "active_task_id_declared": declared if isinstance(declared, str) else None,
        "unresolved_operation_count": len(unresolved),
        "pending_scientific_review_count": operations.get("pending_scientific_review_count", 0),
        "operational_reconciliation_required": bool(
            operations.get("operational_reconciliation_required", False)),
        "next_action_hint": next_hint.get("action") if isinstance(
            next_hint.get("action"), str) else None,
        "rule_commit_local_only": payload.get("rule_commit_local_only"),
        "authorization_verified": False,
        "project_identity_authenticated": False,
        "execution_authorized": False,
        "restart_permitted": False,
        "scientific_completion_verified": False,
        "raw_project_files_returned": False,
    }
