"""Persistent scheduling intents only; never a scientific ledger or executor.

Staging a task, even with a user-supplied authorization ref, never grants execution.
An intent is marked UNCERTAIN *before* any future host dispatch. Restart cannot
re-run it until a trusted external process and evidence reconciliation is built.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import stat
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

from .dependencies import DependencyEvidence, DependencyReviewPort

from pdrw_orchestrator.controller import order_tasks
from pdrw_orchestrator.models import TaskPacket

_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}\Z")
_DB_NAME = "orchestrator.sqlite"
_SCHEMA = """
CREATE TABLE IF NOT EXISTS plans(
  project_id TEXT NOT NULL, plan_id TEXT NOT NULL, digest TEXT NOT NULL,
  created_at TEXT NOT NULL, PRIMARY KEY(project_id, plan_id)
);
CREATE TABLE IF NOT EXISTS tasks(
  project_id TEXT NOT NULL, plan_id TEXT NOT NULL, task_id TEXT NOT NULL,
  digest TEXT NOT NULL, packet_json TEXT NOT NULL, phase TEXT NOT NULL,
  intent_id TEXT, updated_at TEXT NOT NULL, dependency_review_refs TEXT,
  PRIMARY KEY(project_id, plan_id, task_id),
  FOREIGN KEY(project_id, plan_id) REFERENCES plans(project_id, plan_id)
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _identifier(value: str, field: str) -> None:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise ValueError(f"invalid {field}: expected bounded ASCII identifier")


def _overlaps(left: Path, right: Path) -> bool:
    return left == right or left in right.parents or right in left.parents


def _store_path(*, environment: Mapping[str, str] | None = None,
                create: bool = False) -> Path | None:
    env = dict(os.environ if environment is None else environment)
    location = env.get("PDRW_ORCH_RUNTIME_DIR", "")
    if not location:
        raise ValueError("PDRW_ORCH_RUNTIME_DIR_REQUIRED")
    unexpanded = Path(location).expanduser()
    if not unexpanded.is_absolute():
        raise ValueError("PDRW_ORCH_RUNTIME_DIR_NOT_ABSOLUTE")
    directory = unexpanded.resolve()
    # The orchestrator checkout and all authoritative project/CASE roots are protected.
    protected = [Path(__file__).resolve().parents[3]]
    for key in ("PDRW_WORKFLOW_ROOT", "PDRW_CASE_LIBRARY_ROOT"):
        if env.get(key):
            protected.append(Path(env[key]).expanduser().resolve())
    project_map = env.get("PDRW_AGENT_CONFIG")
    if project_map:
        path = Path(project_map).expanduser().resolve()
        protected.append(path.parent)
        if not path.is_file() or path.stat().st_size > 128 * 1024:
            raise ValueError("PDRW_PROJECT_MAP_UNAVAILABLE")
        try:
            mapping = json.loads(path.read_text(encoding="utf-8-sig"))
            projects = mapping.get("projects")
            if not isinstance(projects, dict):
                raise ValueError("invalid project map")
            for value in projects.values():
                if not isinstance(value, dict) or not isinstance(value.get("root"), str):
                    raise ValueError("invalid project root")
                protected.append(Path(value["root"]).expanduser().resolve())
        except (UnicodeError, ValueError) as exc:
            raise ValueError("PDRW_PROJECT_MAP_UNREADABLE") from exc
    if any(_overlaps(directory, root) for root in protected):
        raise ValueError("RUNTIME_DIR_OVERLAPS_PROTECTED_ROOT")
    if create:
        directory.mkdir(parents=True, exist_ok=True)
    elif not directory.is_dir():
        return None
    db_path = directory / _DB_NAME
    if _is_redirected(db_path):
        raise ValueError("RUNTIME_DATABASE_REDIRECTED")
    return db_path


def _is_redirected(path: Path) -> bool:
    # Reject symbolic links and Windows reparse points at the controlled leaf.
    # Not a complete OS sandbox; the runtime root must be operator-owned.
    try:
        info = path.lstat()
    except FileNotFoundError:
        return False
    return path.is_symlink() or bool(
        getattr(info, "st_file_attributes", 0) &
        getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    )


def pilot_attempt_dir(runtime_root: Path, plan_id: str, attempt_id: str) -> Path:
    _identifier(plan_id, "plan_id")
    _identifier(attempt_id, "attempt_id")
    candidate = runtime_root
    for part in ("codex-pilot", plan_id, attempt_id):
        candidate = candidate / part
        if _is_redirected(candidate):
            raise ValueError("PILOT_ATTEMPT_PATH_REDIRECTED")
        if candidate.exists() and not candidate.is_dir():
            raise ValueError("PILOT_ATTEMPT_PATH_NOT_DIRECTORY")
    return candidate


@contextmanager
def _database(path: Path, *, write: bool):
    if write:
        db = sqlite3.connect(str(path), timeout=10)
    else:
        if not path.is_file():
            raise ValueError("PLAN_STORE_MISSING")
        db = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=10)
    db.row_factory = sqlite3.Row
    try:
        db.execute("PRAGMA busy_timeout=10000")
        if write:
            db.execute("BEGIN IMMEDIATE")
            for statement in _SCHEMA.strip().split(";"):
                if statement.strip():
                    db.execute(statement)
            # Backward-compatible migration for v0.2 local databases.
            columns = {row["name"] for row in db.execute("PRAGMA table_info(tasks)")}
            if "dependency_review_refs" not in columns:
                db.execute("ALTER TABLE tasks ADD COLUMN dependency_review_refs TEXT")
        yield db
        if write:
            db.commit()
    except Exception:
        if write:
            db.rollback()
        raise
    finally:
        db.close()


def _hash(value: object) -> str:
    blob = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def stage_plan(plan_id: str, tasks: tuple[TaskPacket, ...],
               *, environment: Mapping[str, str] | None = None) -> dict:
    """Register an immutable operational task graph; never starts any agent."""
    _identifier(plan_id, "plan_id")
    if not 1 <= len(tasks) <= 64:
        raise ValueError("plan task count must be in [1,64]")
    ordered = order_tasks(tasks)
    keys = [task.idempotency_key for task in ordered]
    if any(not key or not _ID.fullmatch(key) for key in keys) or len(set(keys)) != len(keys):
        raise ValueError("TASK_IDEMPOTENCY_KEYS_REQUIRED_UNIQUE")
    project_id = ordered[0].project_id
    _identifier(project_id, "project_id")
    normalized = {t.task_id: t.to_dict() for t in ordered}
    digest = _hash(normalized)
    path = _store_path(environment=environment, create=True)
    assert path is not None
    with _database(path, write=True) as db:
        existing = db.execute(
            "SELECT digest FROM plans WHERE project_id=? AND plan_id=?",
            (project_id, plan_id)).fetchone()
        if existing:
            if existing["digest"] != digest:
                raise ValueError("PLAN_ID_CONFLICT_NO_OVERWRITE")
            status = "ALREADY_STAGED"
        else:
            stamp = _now()
            db.execute(
                "INSERT INTO plans(project_id,plan_id,digest,created_at) VALUES(?,?,?,?)",
                (project_id, plan_id, digest, stamp))
            for task in ordered:
                packet = normalized[task.task_id]
                db.execute(
                    "INSERT INTO tasks(project_id,plan_id,task_id,digest,packet_json,phase,updated_at)"
                    " VALUES(?,?,?,?,?,?,?)",
                    (project_id, plan_id, task.task_id, _hash(packet),
                     json.dumps(packet, ensure_ascii=False, sort_keys=True),
                     "STAGED_NOT_AUTHORIZED", stamp))
            status = "STAGED_NOT_AUTHORIZED"
    return {
        "status": status, "project_id": project_id, "plan_id": plan_id,
        "plan_digest": digest, "task_count": len(ordered),
        "execution_authorized": False, "dispatch_performed": False,
    }


def inspect_plan(project_id: str, plan_id: str,
                 *, environment: Mapping[str, str] | None = None) -> dict:
    """Read-only recovery. Never creates a directory, a DB or an agent process."""
    _identifier(project_id, "project_id")
    _identifier(plan_id, "plan_id")
    path = _store_path(environment=environment, create=False)
    if path is None or not path.is_file():
        return {"status": "NO_PLAN_STORE", "project_id": project_id, "plan_id": plan_id,
                "restart_permitted": False, "execution_authorized": False}
    with _database(path, write=False) as db:
        plan = db.execute(
            "SELECT digest FROM plans WHERE project_id=? AND plan_id=?",
            (project_id, plan_id)).fetchone()
        if plan is None:
            return {"status": "PLAN_NOT_FOUND", "project_id": project_id,
                    "plan_id": plan_id, "restart_permitted": False,
                    "execution_authorized": False}
        rows = db.execute(
            "SELECT task_id,phase,intent_id FROM tasks WHERE project_id=? AND plan_id=? "
            "ORDER BY task_id", (project_id, plan_id)).fetchall()
    tasks = [{"task_id": r["task_id"], "phase": r["phase"],
              "has_recorded_dispatch_intent": r["intent_id"] is not None} for r in rows]
    uncertain = sum(row["has_recorded_dispatch_intent"] for row in tasks)
    return {
        "status": "RECONCILIATION_REQUIRED" if uncertain else "STAGED_NOT_AUTHORIZED",
        "project_id": project_id, "plan_id": plan_id, "plan_digest": plan["digest"],
        "tasks": tasks, "uncertain_intent_count": uncertain,
        "restart_permitted": False, "execution_authorized": False,
        "scientific_completion_verified": False,
    }


def mark_intent_uncertain(project_id: str, plan_id: str, task_id: str, intent_id: str,
                          *, environment: Mapping[str, str] | None = None,
                          dependency_reviewer: DependencyReviewPort | None = None) -> dict:
    """Reserve at most once; future process launch must occur in trusted host.

    This API does not launch any process. Repeating the same ID does NOT retry.
    """
    for key, val in (("project_id", project_id), ("plan_id", plan_id),
                     ("task_id", task_id), ("intent_id", intent_id)):
        _identifier(val, key)
    path = _store_path(environment=environment, create=False)
    if path is None or not path.is_file():
        raise ValueError("PLAN_STORE_MISSING")
    with _database(path, write=True) as db:
        row = db.execute(
            "SELECT phase,intent_id,packet_json FROM tasks WHERE project_id=? AND plan_id=? AND task_id=?",
            (project_id, plan_id, task_id)).fetchone()
        if row is None:
            raise ValueError("TASK_NOT_STAGED")
        if row["intent_id"] is not None:
            if row["intent_id"] != intent_id:
                raise ValueError("UNCERTAIN_INTENT_EXISTS_NO_RETRY")
            status = "ALREADY_MARKED_UNCERTAIN_NO_RETRY"
        else:
            dependencies = tuple(json.loads(row["packet_json"]).get("dependencies", []))
            reviewed_refs = []
            if dependencies:
                if dependency_reviewer is None:
                    raise ValueError("UPSTREAM_EVIDENCE_NOT_VERIFIED_NO_DISPATCH")
                # Only a deliberately injected trusted-host port may inspect the
                # original receipt. The CLI has no option to supply this port.
                reviewed = dependency_reviewer.verify_dependencies(
                    project_id, plan_id, task_id, dependencies)
                if not isinstance(reviewed, tuple) or len(reviewed) != len(dependencies):
                    raise ValueError("HOST_DEPENDENCY_REVIEW_INCOMPLETE")
                by_id = {r.dependency_task_id: r for r in reviewed
                         if isinstance(r, DependencyEvidence)}
                if set(by_id) != set(dependencies) or len(by_id) != len(reviewed):
                    raise ValueError("HOST_DEPENDENCY_REVIEW_MISMATCH")
                reviewed_refs = [{
                    "task_id": dep,
                    "original_receipt_ref": by_id[dep].original_receipt_ref,
                    "artifact_sha256": by_id[dep].artifact_sha256,
                } for dep in dependencies]
            occupied = db.execute(
                "SELECT 1 FROM tasks WHERE project_id=? AND plan_id=? "
                "AND intent_id=? AND task_id<>?",
                (project_id, plan_id, intent_id, task_id)).fetchone()
            if occupied:
                raise ValueError("INTENT_ID_ALREADY_RESERVED")
            db.execute(
                "UPDATE tasks SET phase='INTENT_UNCERTAIN', intent_id=?, updated_at=?, "
                "dependency_review_refs=? WHERE project_id=? AND plan_id=? AND task_id=? AND intent_id IS NULL",
                (intent_id, _now(), json.dumps(reviewed_refs, sort_keys=True),
                 project_id, plan_id, task_id))
            status = "INTENT_UNCERTAIN_NO_DISPATCH"
    return {
        "status": status, "project_id": project_id, "plan_id": plan_id,
        "task_id": task_id, "attempt_id": intent_id, "dispatch_performed": False,
        "execution_authorized": False, "restart_permitted": False,
        "next": "RECONCILE_TRUSTED_HOST_PROCESS_AND_ORIGINAL_PDRW_RECEIPT",
    }


def assess_recovery(local: dict, upstream: dict) -> dict:
    """Merge two *advisory* statuses; never turn them into a resume permit."""
    if local.get("project_id") != upstream.get("project_id"):
        reason = "PROJECT_ID_MISMATCH"
    elif upstream.get("bridge_status") != "SOURCE_REVIEW_ONLY":
        reason = "UPSTREAM_SOURCE_UNAVAILABLE"
    elif upstream.get("source_status") != "SOURCE_REVIEW_REQUIRED":
        reason = "UPSTREAM_SOURCE_REVIEW_REQUIRED"
    elif (upstream.get("unresolved_operation_count", 0)
          or upstream.get("operational_reconciliation_required")):
        reason = "UPSTREAM_OPERATION_RECONCILIATION"
    elif local.get("uncertain_intent_count", 0):
        reason = "LOCAL_INTENT_RECONCILIATION"
    elif local.get("status") != "STAGED_NOT_AUTHORIZED":
        reason = "LOCAL_PLAN_NOT_STAGED"
    else:
        reason = "SOURCE_REVIEW_ONLY_NO_EXECUTION_AUTH"
    return {
        "status": reason, "project_id": local.get("project_id"),
        "plan_id": local.get("plan_id"),
        "execution_authorized": False, "restart_permitted": False,
        "scientific_completion_verified": False,
    }



def has_exact_intent(project_id: str, plan_id: str, task_id: str, attempt_id: str) -> bool:
    """Read-only exact intent lookup; a match is not a dispatch permission."""
    for name, value in (("project_id", project_id), ("plan_id", plan_id),
                        ("task_id", task_id), ("attempt_id", attempt_id)):
        _identifier(value, name)
    path = _store_path(create=False)
    if path is None or not path.is_file() or path.is_symlink():
        return False
    with _database(path, write=False) as db:
        row = db.execute(
            "SELECT intent_id,phase FROM tasks WHERE project_id=? AND plan_id=? AND task_id=?",
            (project_id, plan_id, task_id)).fetchone()
    return row is not None and row["intent_id"] == attempt_id and row["phase"] == "INTENT_UNCERTAIN"
