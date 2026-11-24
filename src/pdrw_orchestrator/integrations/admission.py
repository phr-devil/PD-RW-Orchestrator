"""Read-only DEV admission preview via the actual pinned upstream host API.

The upstream public execution-preflight CLI is a different synthetic-only
contract. This adapter never calls submit, register, receipt write or a model.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile

from .source_checks import _source_settings
from ..runtime.host_checks import _python_path

_FIELDS = frozenset({
    "schema_version", "project_id", "operation_id", "task_id", "action",
    "runner_id", "task_spec_sha256", "code_sha256", "dataset_manifest_sha256",
    "time_limit_seconds", "cpu_limit", "gpu_count", "network", "data_split",
})
_IDS = ("project_id", "operation_id", "task_id", "runner_id")
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}\Z")
_FALSE = ("original_user_grant_verified", "host_os_identity_verified",
          "os_acl_enforced", "job_supervisor_connected", "gpu_limits_enforced",
          "execution_authorized", "execute_performed")
_ENTRY = """
import importlib.metadata, json, sys
try:
    import pdrw_agent
    if (importlib.metadata.version("pdrw-agent") != "1.0.0rc1" or
            getattr(pdrw_agent, "__version__", None) != "1.0.0rc1"):
        raise ValueError("version")
    from pdrw_agent.config import Settings
    from pdrw_agent.host.authorization import preview_dev_admission
    payload = json.loads(sys.stdin.buffer.read(8193).decode("utf-8"))
    print(json.dumps(preview_dev_admission(Settings.load(), payload)))
except Exception:
    print('{"status":"UPSTREAM_PREVIEW_REJECTED"}')
    sys.exit(3)
"""


def preview_admission(proposal, *, python_executable=None, environment=None):
    base = {
        "status": "DEV_ADMISSION_PREVIEW_UNAVAILABLE",
        "execution_authorized": False, "execute_performed": False,
        "original_user_grant_verified": False, "host_os_identity_verified": False,
        "new_author_grant_required": None, "restart_permitted": False,
        "scientific_validity_verified": False, "model_calls_requested": 0,
        "upstream_revision_authenticated": False,
    }
    if (not isinstance(proposal, dict) or set(proposal) != _FIELDS
            or proposal.get("schema_version") != "pdrw-dev-plan-v1"
            or any(not isinstance(proposal[k], str) or not _ID.fullmatch(proposal[k])
                   for k in _IDS)):
        return {**base, "status": "DEV_PROPOSAL_ENVELOPE_INVALID"}
    try:
        encoded = json.dumps(proposal, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=True, allow_nan=False).encode("utf-8")
        if len(encoded) > 8192:
            return {**base, "status": "DEV_PROPOSAL_ENVELOPE_INVALID"}
        base.update({k: proposal[k] for k in _IDS})
        fingerprint = hashlib.sha256(encoded).hexdigest()
        base["plan_sha256"] = fingerprint
        env = dict(os.environ if environment is None else environment)
        before, error = _source_settings(proposal["project_id"], env)
        if error:
            return {**base, "status": "DEV_ADMISSION_SOURCE_UNAVAILABLE", "source_status": error}
        python = _python_path(python_executable)
        with tempfile.TemporaryFile(mode="w+b") as source, tempfile.TemporaryFile(mode="w+b") as sink:
            source.write(encoded)
            source.seek(0)
            proc = subprocess.run([python, "-I", "-B", "-c", _ENTRY], stdin=source,
                stdout=sink, stderr=subprocess.DEVNULL, env=env, timeout=30, check=False)
            sink.seek(0)
            raw = sink.read(16385)
        if proc.returncode != 0:
            return {**base, "status": "DEV_ADMISSION_UPSTREAM_REJECTED"}
        if len(raw) > 16384:
            return {**base, "status": "DEV_ADMISSION_RESPONSE_OVERSIZE"}
        after, error = _source_settings(proposal["project_id"], env)
        if error or before != after:
            return {**base, "status": "DEV_ADMISSION_SOURCE_CHANGED"}
        response = json.loads(raw.decode("utf-8-sig"))
        if (not isinstance(response, dict)
                or any(response.get(k) != proposal[k] for k in (*_IDS, "action"))
                or response.get("plan_sha256") != fingerprint
                or any(response.get(k) is not False for k in _FALSE)
                or response.get("authorization_state") != "UNVERIFIED"
                or response.get("runtime_state") != "UNSTARTED"
                or response.get("evidence_state") != "NOT_REVIEWED"
                or response.get("science_state") != "NOT_REVIEWED"):
            return {**base, "status": "DEV_ADMISSION_RESPONSE_CONFLICT"}
        status = response.get("status")
        readiness = response.get("project_machine_readiness")
        if (not isinstance(readiness, str) or not re.fullmatch(r"[A-Z][A-Z0-9_]{0,79}", readiness)
                or status != ("TRUSTED_HOST_NOT_CONNECTED" if readiness == "MACHINE_METADATA_READY"
                              else "PROJECT_MACHINE_STATE_BLOCKED")):
            return {**base, "status": "DEV_ADMISSION_RESPONSE_CONFLICT"}
        return {**base, "status": "DEV_ADMISSION_PREVIEW_ONLY", "upstream_status": status,
                "action": proposal["action"], "project_machine_readiness": readiness,
                "proposal_validated_by_installed_upstream": True, "source_fingerprints": before,
                "authorization_status": "EXISTING_SCOPE_VERIFIER_UNAVAILABLE",
                "next": "CONNECT_INDEPENDENT_TRUSTED_HOST_WITH_ORIGINAL_SCOPE"}
    except subprocess.TimeoutExpired:
        return {**base, "status": "DEV_ADMISSION_TIMEOUT_NO_RETRY"}
    except (OSError, ValueError, TypeError, KeyError, UnicodeError):
        return {**base, "status": "DEV_ADMISSION_REQUEST_OR_RESPONSE_REJECTED"}
