"""M1-B local storage acceptance, no real scientific projects or agent processes."""
import json
import sqlite3
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from pdrw_orchestrator.models import TaskPacket
from pdrw_orchestrator.runtime.store import (
    assess_recovery, inspect_plan, mark_intent_uncertain, stage_plan,
)

ROOT = Path(__file__).resolve().parents[1]


def env(tmp_path):
    return {"PDRW_ORCH_RUNTIME_DIR": str(tmp_path / "private-runtime")}


def plan():
    return (
        TaskPacket(task_id="A", project_id="P19", task_type="discovery",
                   objective="Synthetic only", idempotency_key="A-stable"),
        TaskPacket(task_id="B", project_id="P19", task_type="analysis",
                   objective="Synthetic review", dependencies=("A",),
                   idempotency_key="B-stable"),
    )


def test_restart_safe_and_intent_never_retried(tmp_path):
    e = env(tmp_path)
    result = stage_plan("plan1", plan(), environment=e)
    assert result["status"] == "STAGED_NOT_AUTHORIZED"
    # Same immutable input across distinct calls (simulates a new process).
    assert stage_plan("plan1", plan(), environment=e)["status"] == "ALREADY_STAGED"
    assert inspect_plan("P19", "plan1", environment=e)["uncertain_intent_count"] == 0
    reserved = mark_intent_uncertain("P19", "plan1", "A", "attempt-1", environment=e)
    assert reserved["status"] == "INTENT_UNCERTAIN_NO_DISPATCH"
    assert reserved["dispatch_performed"] is False
    after_restart = inspect_plan("P19", "plan1", environment=e)
    assert after_restart["status"] == "RECONCILIATION_REQUIRED"
    assert after_restart["restart_permitted"] is False
    again = mark_intent_uncertain("P19", "plan1", "A", "attempt-1", environment=e)
    assert again["status"] == "ALREADY_MARKED_UNCERTAIN_NO_RETRY"
    with pytest.raises(ValueError, match="UNCERTAIN_INTENT_EXISTS_NO_RETRY"):
        mark_intent_uncertain("P19", "plan1", "A", "attempt-2", environment=e)


def test_immutable_stage_conflict_never_overwrites(tmp_path):
    e = env(tmp_path)
    stage_plan("plan1", plan(), environment=e)
    changed = (TaskPacket(task_id="A", project_id="P19", task_type="discovery",
                          objective="Different task"), plan()[1])
    with pytest.raises(ValueError, match="PLAN_ID_CONFLICT"):
        stage_plan("plan1", changed, environment=e)
    assert len(inspect_plan("P19", "plan1", environment=e)["tasks"]) == 2


def test_missing_store_inspection_does_not_create_files(tmp_path):
    e = env(tmp_path)
    assert inspect_plan("P19", "plan1", environment=e)["status"] == "NO_PLAN_STORE"
    assert not (tmp_path / "private-runtime").exists()


def test_store_must_not_overlap_checkout_or_authoritative_roots(tmp_path):
    e = {"PDRW_ORCH_RUNTIME_DIR": "."}
    with pytest.raises(ValueError, match="NOT_ABSOLUTE"):
        stage_plan("plan1", plan(), environment=e)
    project = tmp_path / "research-original"
    project.mkdir()
    pmap = tmp_path / "mapping" / "map.json"
    pmap.parent.mkdir()
    pmap.write_text(json.dumps({"projects": {"P19": {"root": str(project)}}}))
    e = {"PDRW_ORCH_RUNTIME_DIR": str(project / "runtime"),
         "PDRW_AGENT_CONFIG": str(pmap)}
    with pytest.raises(ValueError, match="OVERLAPS_PROTECTED_ROOT"):
        stage_plan("plan1", plan(), environment=e)


def test_invalid_dag_does_not_write_store(tmp_path):
    e = env(tmp_path)
    bad = (TaskPacket(task_id="X", project_id="P19", task_type="analysis",
                      objective="x", dependencies=("MISSING",)),)
    with pytest.raises(ValueError, match="missing dependency"):
        stage_plan("plan1", bad, environment=e)
    assert not (tmp_path / "private-runtime").exists()


def test_recovery_never_returns_execution_permission(tmp_path):
    e = env(tmp_path)
    stage_plan("plan1", plan(), environment=e)
    local = inspect_plan("P19", "plan1", environment=e)
    upstream = {"bridge_status": "SOURCE_REVIEW_ONLY", "project_id": "P19",
                "source_status": "SOURCE_REVIEW_REQUIRED",
                "unresolved_operation_count": 0,
                "operational_reconciliation_required": False}
    result = assess_recovery(local, upstream)
    assert result["status"] == "SOURCE_REVIEW_ONLY_NO_EXECUTION_AUTH"
    assert result["execution_authorized"] is False
    mark_intent_uncertain("P19", "plan1", "A", "attempt-1", environment=e)
    result = assess_recovery(inspect_plan("P19", "plan1", environment=e), upstream)
    assert result["status"] == "LOCAL_INTENT_RECONCILIATION"
    upstream["unresolved_operation_count"] = 2
    assert assess_recovery(local, upstream)["status"] == "UPSTREAM_OPERATION_RECONCILIATION"
    upstream["source_status"] = "BLOCKED_PROJECT_IDENTITY"
    assert assess_recovery(local, upstream)["status"] == "UPSTREAM_SOURCE_REVIEW_REQUIRED"


def test_storage_does_not_become_science_ledger(tmp_path):
    e = env(tmp_path)
    stage_plan("plan1", plan(), environment=e)
    db_path = tmp_path / "private-runtime" / "orchestrator.sqlite"
    con = sqlite3.connect(db_path)
    try:
        assert {row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")} == {"plans", "tasks"}
        assert all("RESULT" not in row[0].upper() and "RUN" not in row[0].upper()
                   for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'"))
    finally:
        con.close()


def test_example_plan_contract_matches_schema():
    from jsonschema import RefResolver
    source = json.loads((ROOT / "examples/operational-plan.example.json").read_text())
    schema = json.loads((ROOT / "schemas/plan.schema.json").read_text())
    resolver = RefResolver(base_uri=(ROOT / "schemas").as_uri() + "/", referrer=schema)
    Draft202012Validator(schema, resolver=resolver).validate(source)
