"""Synthetic pilot process lifecycle; operational facts only, no restart rights."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from .host_checks import inspect_process


def _stamp():
    return datetime.now(timezone.utc).isoformat()


def _hash(data):
    return hashlib.sha256(data).hexdigest()


def _read(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError("LIFECYCLE_FILE_MISSING")
    with path.open("rb") as f:
        raw = f.read(16385)
    if len(raw) > 16384:
        raise ValueError("LIFECYCLE_FILE_TOO_LARGE")
    obj = json.loads(raw)
    if not isinstance(obj, dict):
        raise ValueError("LIFECYCLE_OBJECT_REQUIRED")
    return obj, _hash(raw)


class PilotLifecycle:
    """One fixed pilot attempt, bound to its persisted intent and contract."""
    def __init__(self, directory: Path, *, plan_id: str, attempt_id: str,
                 contract_sha256: str, task_id: str = "CODEX-READ-001"):
        if task_id not in ("CODEX-READ-001", "CLAUDE-REVIEW-001"):
            raise ValueError("LIFECYCLE_TASK_OUT_OF_SCOPE")
        self.directory = directory
        self.binding = {
            "project_id": "PILOT", "task_id": task_id,
            "plan_id": plan_id, "attempt_id": attempt_id,
            "contract_sha256": contract_sha256,
        }

    def record(self, name, payload):
        if name not in ("launch-intent", "child-started", "child-ended"):
            raise ValueError("LIFECYCLE_EVENT_INVALID")
        parent = {"launch-intent": None, "child-started": "launch-intent",
                  "child-ended": "child-started"}[name]
        previous = None
        if parent:
            try:
                _, previous = _read(self.directory / (parent + ".json"))
            except ValueError:
                if name != "child-ended" or payload["outcome"] != "LAUNCH_FAILED":
                    raise
                _, previous = _read(self.directory / "launch-intent.json")
        obj = {"schema_version": "1.0", **self.binding, "event": name,
               "observed_utc": _stamp(), "previous_sha256": previous, **payload}
        data = json.dumps(obj, sort_keys=True, allow_nan=False).encode()
        if len(data) > 16384:
            raise ValueError("LIFECYCLE_EVENT_TOO_LARGE")
        # Exclusive append-only event files; a partial write is unresolved.
        with (self.directory / (name + ".json")).open("xb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())


def _stop_owned_child(proc):
    """Only the direct child handle created by this call, never arbitrary PID."""
    try:
        if proc.poll() is None:
            proc.kill()
        return proc.wait(timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return None


def run_tracked_child(args, prompt, wall_seconds, lifecycle, *,
                      stdout=subprocess.DEVNULL, cwd=None):
    """Internal runner for fixed synthetic adapter. No process-tree claim."""
    # Prewrite bounded stdin to a temporary OS file. Windows pipe writes can
    # block before communicate() enforces a timeout if the child never reads.
    with tempfile.TemporaryFile(mode="w+b") as stdin:
        stdin.write(prompt.encode("utf-8"))
        stdin.seek(0)
        lifecycle.record("launch-intent", {"wall_seconds": wall_seconds})
        try:
            proc = subprocess.Popen(args, stdin=stdin,
                                    stdout=stdout, stderr=subprocess.DEVNULL, cwd=cwd)
        except OSError:
            lifecycle.record("child-ended", {"outcome": "LAUNCH_FAILED", "returncode": None})
            return None, "PROCESS_LAUNCH_FAILED_UNCERTAIN"
    try:
        observation = inspect_process(proc.pid)
        lifecycle.record("child-started", {
            "pid": proc.pid, "identity": observation.get("identity"),
            "identity_status": observation["status"],
        })
        try:
            proc.wait(timeout=wall_seconds)
        except subprocess.TimeoutExpired:
            code = _stop_owned_child(proc)
            lifecycle.record("child-ended", {"outcome": "TIMEOUT",
                                               "returncode": code})
            return None, "TIMEOUT_PROCESS_STATE_UNCERTAIN"
        lifecycle.record("child-ended", {"outcome": "EXITED", "returncode": proc.returncode})
        return proc.returncode, None
    except BaseException:
        # The original reserved intent remains uncertain even if cleanup succeeds.
        _stop_owned_child(proc)
        raise


def inspect_lifecycle(directory: Path, *, plan_id: str, attempt_id: str,
                      contract_sha256: str, task_id: str = "CODEX-READ-001") -> dict:
    """Inspect only this attempt's recorded direct-child events, not Agent claims."""
    result = {"status": "LIFECYCLE_RECONCILIATION_REQUIRED",
              "restart_permitted": False, "cancel_permitted": False,
              "execution_authorized": False, "scientific_validity_verified": False,
              "descendant_processes_verified": False,
              "original_operation_binding_verified": False}
    binding = PilotLifecycle(directory, plan_id=plan_id, attempt_id=attempt_id,
                             contract_sha256=contract_sha256, task_id=task_id).binding
    def load(name, previous):
        obj, digest = _read(directory / (name + ".json"))
        if (obj.get("event") != name or obj.get("schema_version") != "1.0"
                or obj.get("previous_sha256") != previous
                or any(obj.get(k) != v for k, v in binding.items())):
            raise ValueError("LIFECYCLE_BINDING_MISMATCH")
        return obj, digest
    try:
        if directory.is_symlink() or not directory.is_dir():
            return result
        contract, digest = _read(directory / "task-contract.json")
        if (digest != contract_sha256 or contract.get("project_id") != "PILOT"
                or contract.get("task_id") != task_id
                or contract.get("required_effects") != []):
            return result
        launch, digest = load("launch-intent", None)
        if type(launch.get("wall_seconds")) is not int or not 1 <= launch["wall_seconds"] <= 300:
            return result
        start_path = directory / "child-started.json"
        end_path = directory / "child-ended.json"
        if not start_path.exists() and not start_path.is_symlink():
            if end_path.exists():
                end, _ = load("child-ended", digest)
                if end.get("outcome") == "LAUNCH_FAILED" and end.get("returncode") is None:
                    return {**result, "status": "LIFECYCLE_LAUNCH_FAILED_RECORDED"}
            return result
        started, digest = load("child-started", digest)
        pid = started.get("pid")
        if type(pid) is not int or not 1 <= pid <= 2**31-1:
            return result
        identity = started.get("identity")
        if identity is not None:
            import math
            import re
            if (not isinstance(identity, dict) or identity.get("pid") != pid
                    or type(identity.get("created_at")) not in (int, float)
                    or not 0 < identity["created_at"] < 1e12
                    or not math.isfinite(identity["created_at"])
                    or not isinstance(identity.get("exe_path_sha256"), str)
                    or not re.fullmatch(r"[0-9a-f]{64}", identity["exe_path_sha256"])):
                return result
        if end_path.exists() or end_path.is_symlink():
            ended, _ = load("child-ended", digest)
            code = ended.get("returncode")
            if ended.get("outcome") == "EXITED" and type(code) is int:
                return {**result, "status": "LIFECYCLE_DIRECT_CHILD_EXIT_RECORDED",
                        "returncode": code, "pid": pid}
            if ended.get("outcome") == "TIMEOUT" and (code is None or type(code) is int):
                return {**result, "status": "LIFECYCLE_TIMEOUT_RECORDED",
                        "returncode": code, "pid": pid}
            return result
        if identity is not None:
            observed = inspect_process(pid, expected_created_at=identity.get("created_at"),
                                       expected_exe_path_sha256=identity.get("exe_path_sha256"))
            return {**result, "process_observation": observed["status"]}
    except (OSError, ValueError, TypeError, KeyError, UnicodeError):
        pass
    return result



def lifecycle_matches_invocation(check: dict, status: str, returncode: int | None) -> bool:
    """Never accept a reported result without the corresponding local child event."""
    if status == "TIMEOUT_PROCESS_STATE_UNCERTAIN":
        return check.get("status") == "LIFECYCLE_TIMEOUT_RECORDED" and returncode is None
    if status == "PROCESS_LAUNCH_FAILED_UNCERTAIN":
        return check.get("status") == "LIFECYCLE_LAUNCH_FAILED_RECORDED" and returncode is None
    return (check.get("status") == "LIFECYCLE_DIRECT_CHILD_EXIT_RECORDED"
            and type(returncode) is int and check.get("returncode") == returncode)
