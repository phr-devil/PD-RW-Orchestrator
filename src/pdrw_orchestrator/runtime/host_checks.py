"""Operator-only local observations; no grants, cancellation or restart.

A source receipt does not bind a PID to a task. A matching process identity
only describes that local process at the sampling instant.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Mapping

from pdrw_orchestrator.integrations.source_checks import inspect_source_chain

_EXPECTED_VERSION = "1.0.0rc1"
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_VERSION = re.compile(r"[A-Za-z0-9.+-]{1,80}\Z")
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}\Z")
# Isolated interpreter, installed package only; never import the CLI or
# invoke project operations merely to inspect installation metadata.
_PROBE = """
import hashlib, importlib.metadata, importlib.util, json
from pathlib import Path
try:
    import pdrw_agent
    spec = importlib.util.find_spec("pdrw_agent.cli")
    if spec is None or spec.origin is None:
        raise ValueError("missing CLI")
    with Path(spec.origin).open("rb") as f:
        data = f.read(2 * 1024 * 1024 + 1)
    if len(data) > 2 * 1024 * 1024:
        raise ValueError("oversize CLI")
    print(json.dumps({
        "package_version": importlib.metadata.version("pdrw-agent"),
        "source_version": getattr(pdrw_agent, "__version__", None),
        "cli_sha256": hashlib.sha256(data).hexdigest(),
    }))
except (ImportError, OSError, ValueError):
    print("{}")
"""


def _flags() -> dict:
    return {
        "execution_authorized": False,
        "author_scope_verified": False,
        "scientific_validity_verified": False,
        "restart_permitted": False,
        "cancel_permitted": False,
        "operation_process_binding_verified": False,
    }


def _python_path(executable: str | None) -> str:
    # Do NOT resolve symlinks: a venv's python symlink must retain its
    # launcher location or the selected virtual environment may be lost.
    candidate = Path(executable or sys.executable).expanduser().absolute()
    if not candidate.is_file():
        raise ValueError("HOST_PYTHON_UNAVAILABLE")
    return str(candidate)


def probe_installation(*, python_executable: str | None = None,
                       expected_version: str = _EXPECTED_VERSION,
                       expected_cli_sha256: str | None = None,
                       environment: Mapping[str, str] | None = None) -> dict:
    """Compare metadata, imported source and optional operator reference hash.

    Not a full revision, Skill, MCP or machine authentication.
    """
    result = {**_flags(), "full_revision_authenticated": False,
              "skill_mcp_alignment_verified": False}
    if (not isinstance(expected_version, str) or not _VERSION.fullmatch(expected_version)
            or (expected_cli_sha256 is not None and (
                not isinstance(expected_cli_sha256, str)
                or not _SHA.fullmatch(expected_cli_sha256)))):
        return {**result, "status": "HOST_REFERENCE_INVALID"}
    try:
        python = _python_path(python_executable)
        with tempfile.TemporaryFile(mode="w+b") as sink:
            proc = subprocess.run(
                [python, "-I", "-B", "-c", _PROBE],
                stdout=sink, stderr=subprocess.DEVNULL, check=False,
                timeout=15, env=dict(os.environ if environment is None else environment),
            )
            sink.seek(0)
            raw = sink.read(8193)
        if proc.returncode != 0 or len(raw) > 8192:
            return {**result, "status": "HOST_INSTALLATION_PROBE_FAILED"}
        obj = json.loads(raw.decode("utf-8"))
    except (OSError, ValueError, UnicodeError, subprocess.TimeoutExpired):
        return {**result, "status": "HOST_INSTALLATION_PROBE_UNAVAILABLE"}
    if not isinstance(obj, dict):
        return {**result, "status": "HOST_INSTALLATION_PROBE_FAILED"}
    version, source, digest = (obj.get(k) for k in (
        "package_version", "source_version", "cli_sha256"))
    if (not all(isinstance(x, str) and _VERSION.fullmatch(x) for x in (version, source))
            or not isinstance(digest, str) or not _SHA.fullmatch(digest)):
        return {**result, "status": "HOST_INSTALLATION_PROBE_FAILED"}
    result.update(package_version=version, source_version=source,
                  cli_sha256=digest, expected_version=expected_version,
                  cli_reference_matched=(digest == expected_cli_sha256
                                         if expected_cli_sha256 is not None else None))
    if version != source or source != expected_version:
        return {**result, "status": "HOST_VERSION_MISMATCH"}
    if expected_cli_sha256 is not None and digest != expected_cli_sha256:
        return {**result, "status": "HOST_CLI_HASH_MISMATCH"}
    return {**result, "status": "HOST_INSTALLATION_MATCHED_LOCALLY"}


def _process_identity(process) -> dict:
    # No argv, cwd, environment, username or raw executable path is exported.
    created = process.create_time()
    exe = process.exe()
    if not isinstance(exe, str) or not exe or not math.isfinite(created) or created <= 0:
        raise ValueError("PROCESS_IDENTITY_INCOMPLETE")
    path = os.path.normcase(os.path.abspath(exe))
    return {"pid": process.pid, "created_at": created,
            "exe_path_sha256": hashlib.sha256(os.fsencode(path)).hexdigest()}


def inspect_process(pid: int, *, expected_created_at: float | None = None,
                    expected_exe_path_sha256: str | None = None) -> dict:
    """Sample a local PID; compare against a previously recorded host baseline.

    The caller must supply both baseline fields or neither. A new snapshot
    cannot retroactively prove that a PID belongs to an older task.
    """
    base = {**_flags(), "process_liveness_verified": False,
            "same_process_as_baseline": False, "sample_scope": "LOCAL_INSTANT_ONLY"}
    has_baseline = expected_created_at is not None or expected_exe_path_sha256 is not None
    if type(pid) is not int or not 1 <= pid <= 2**31 - 1:
        return {**base, "status": "PROCESS_INPUT_INVALID"}
    if has_baseline and (
        type(expected_created_at) not in (int, float)
        or not math.isfinite(expected_created_at) or expected_created_at <= 0
        or not isinstance(expected_exe_path_sha256, str)
        or not _SHA.fullmatch(expected_exe_path_sha256)
    ):
        return {**base, "status": "PROCESS_BASELINE_INVALID"}
    try:
        import psutil
    except ImportError:
        return {**base, "status": "PROCESS_OBSERVER_NOT_INSTALLED"}
    try:
        p = psutil.Process(pid)
        first = _process_identity(p)
        status = p.status()
        # Fresh handle and second identity sample: avoid cached create_time
        # being mistaken for a reused PID while observing the process.
        fresh = psutil.Process(pid)
        second = _process_identity(fresh)
        if first != second or not fresh.is_running():
            return {**base, "status": "PROCESS_CHANGED_DURING_SAMPLE"}
        if status in (psutil.STATUS_ZOMBIE, psutil.STATUS_DEAD):
            return {**base, "status": "PROCESS_NOT_LIVE_AT_SAMPLE"}
        if has_baseline and (
            first["created_at"] != expected_created_at
            or first["exe_path_sha256"] != expected_exe_path_sha256
        ):
            return {**base, "status": "PROCESS_IDENTITY_MISMATCH"}
        return {**base, "status": ("PROCESS_MATCH_ALIVE" if has_baseline
                                   else "PROCESS_OBSERVED_UNBOUND"),
                "identity": first,
                "process_liveness_verified": True,
                "same_process_as_baseline": has_baseline}
    except psutil.NoSuchProcess:
        return {**base, "status": "PROCESS_ABSENT_AT_SAMPLE"}
    except (psutil.Error, OSError, ValueError):
        return {**base, "status": "PROCESS_STATE_UNKNOWN"}


def audit_host(project_id: str, *, operation_id: str | None = None,
               run_id: str | None = None, task_id: str | None = None,
               python_executable: str | None = None,
               expected_version: str = _EXPECTED_VERSION,
               expected_cli_sha256: str | None = None,
               environment: Mapping[str, str] | None = None) -> dict:
    """Combine installed-version and original-source read-only observations.

    No upstream RC interface authenticates H6 or binds process identity to
    original receipts. An unavailable verifier is not a request for new H6.
    """
    result = {**_flags(), "project_id": project_id,
              "authorization_status": "EXISTING_SCOPE_VERIFIER_UNAVAILABLE",
              "new_author_grant_required": None,
              "project_identity_authenticated": False,
              "process_liveness_verified": False,
              "full_revision_authenticated": False,
              "source": None}
    for ident in (project_id, task_id, operation_id, run_id):
        if ident is not None and (not isinstance(ident, str) or not _ID.fullmatch(ident)):
            return {**result, "project_id": None, "status": "HOST_IDENTIFIER_INVALID"}
    if not project_id:
        return {**result, "status": "HOST_IDENTIFIER_INVALID"}
    options = dict(python_executable=python_executable, expected_version=expected_version,
                   expected_cli_sha256=expected_cli_sha256, environment=environment)
    initial = probe_installation(**options)
    result["installation"] = initial
    if initial["status"] != "HOST_INSTALLATION_MATCHED_LOCALLY":
        return {**result, "status": "HOST_INSTALLATION_RECONCILIATION_REQUIRED"}
    source = inspect_source_chain(
        project_id, operation_id=operation_id, run_id=run_id,
        python_executable=python_executable, environment=environment)
    after = probe_installation(**options)
    if initial != after:
        return {**result, "status": "HOST_INSTALLATION_CHANGED_DURING_CHECK"}
    result["source"] = source
    if source.get("project_id") != project_id:
        return {**result, "source": None, "status": "HOST_SOURCE_IDENTITY_MISMATCH"}
    if task_id is not None:
        records = [source.get(k) for k in ("operation", "run") if source.get(k) is not None]
        if not records or any(row.get("task_id_declared") != task_id for row in records):
            return {**result, "status": "HOST_SOURCE_TASK_MISMATCH_OR_UNKNOWN"}
    if source.get("verification_status") != "SOURCE_READ_ONLY_CHECKS_COMPLETE":
        return {**result, "status": "HOST_SOURCE_RECONCILIATION_REQUIRED"}
    return {**result, "status": "HOST_READ_ONLY_CHECKS_COMPLETE"}
