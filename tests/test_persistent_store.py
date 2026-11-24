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
                          objective="Different task", idempotency_key="A-stable"), plan()[1])
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
    from referencing import Registry, Resource
    source = json.loads((ROOT / "examples/operational-plan.example.json").read_text())
    schema = json.loads((ROOT / "schemas/plan.schema.json").read_text())
    schema["$id"] = (ROOT / "schemas/plan.schema.json").as_uri()
    task_schema = json.loads((ROOT / "schemas/task.schema.json").read_text())
    registry = Registry().with_resource(
        (ROOT / "schemas/task.schema.json").as_uri(),
        Resource.from_contents(task_schema),
    )
    Draft202012Validator(schema, registry=registry).validate(source)


def test_unique_idempotency_keys_required_before_staging(tmp_path):
    e = env(tmp_path)
    missing = (TaskPacket(task_id="A", project_id="P19", task_type="discovery",
                          objective="a"),)
    with pytest.raises(ValueError, match="TASK_IDEMPOTENCY_KEYS_REQUIRED_UNIQUE"):
        stage_plan("plan-missing", missing, environment=e)
    duplicate = (
        TaskPacket(task_id="A", project_id="P19", task_type="discovery",
                   objective="a", idempotency_key="same-key"),
        TaskPacket(task_id="B", project_id="P19", task_type="discovery",
                   objective="b", idempotency_key="same-key"),
    )
    with pytest.raises(ValueError, match="TASK_IDEMPOTENCY_KEYS_REQUIRED_UNIQUE"):
        stage_plan("plan-duplicate", duplicate, environment=e)
    assert not (tmp_path / "private-runtime").exists()


def test_dependent_intent_cannot_be_reserved_without_real_evidence(tmp_path):
    e = env(tmp_path)
    stage_plan("plan1", plan(), environment=e)
    with pytest.raises(ValueError, match="UPSTREAM_EVIDENCE_NOT_VERIFIED_NO_DISPATCH"):
        mark_intent_uncertain("P19", "plan1", "B", "attempt-B", environment=e)
    assert inspect_plan("P19", "plan1", environment=e)["uncertain_intent_count"] == 0


def test_attempt_ids_unique_within_operational_plan(tmp_path):
    e = env(tmp_path)
    independent = (
        TaskPacket(task_id="A", project_id="P19", task_type="discovery",
                   objective="a", idempotency_key="A-key"),
        TaskPacket(task_id="B", project_id="P19", task_type="discovery",
                   objective="b", idempotency_key="B-key"),
    )
    stage_plan("plan2", independent, environment=e)
    mark_intent_uncertain("P19", "plan2", "A", "attempt-1", environment=e)
    with pytest.raises(ValueError, match="INTENT_ID_ALREADY_RESERVED"):
        mark_intent_uncertain("P19", "plan2", "B", "attempt-1", environment=e)


def test_replan_cannot_duplicate_unresolved_task_or_idempotency_key(tmp_path):
    e = env(tmp_path)
    stage_plan("one", (plan()[0],), environment=e)
    mark_intent_uncertain("P19","one","A","attempt-1",environment=e)
    for name, task in (
        ("same-task", TaskPacket("A","P19","review","Changed objective",idempotency_key="new-key")),
        ("same-key", TaskPacket("C","P19","review","Alternate",idempotency_key="A-stable")),
        ("same-attempt", TaskPacket("D","P19","review","Alternate",idempotency_key="D-key")),
    ):
        stage_plan(name,(task,),environment=e)
        attempt = "attempt-1" if name == "same-attempt" else "attempt-2"
        with pytest.raises(ValueError,match="CROSS_PLAN_UNRESOLVED_INTENT_NO_RETRY"):
            mark_intent_uncertain("P19",name,task.task_id,attempt,environment=e)
        assert inspect_plan("P19",name,environment=e)["uncertain_intent_count"]==0
    independent=TaskPacket("E","P19","review","Independent task",idempotency_key="E-key")
    stage_plan("independent",(independent,),environment=e)
    assert mark_intent_uncertain("P19","independent","E","attempt-3",environment=e)["status"]=="INTENT_UNCERTAIN_NO_DISPATCH"


@pytest.mark.parametrize("statement", [
    "UPDATE tasks SET packet_json='{}' WHERE task_id='A'",
    "UPDATE tasks SET phase='COMPLETE' WHERE task_id='A'",
    "DELETE FROM tasks WHERE task_id='B'",
    "UPDATE plans SET digest='forged'",
])
def test_corrupt_plan_never_reused_or_reserved(tmp_path,statement,monkeypatch):
    from pdrw_orchestrator.runtime.store import has_exact_intent
    e=env(tmp_path)
    stage_plan("one",plan(),environment=e)
    with sqlite3.connect(tmp_path/"private-runtime"/"orchestrator.sqlite") as db:
        db.execute(statement)
    monkeypatch.setenv("PDRW_ORCH_RUNTIME_DIR",e["PDRW_ORCH_RUNTIME_DIR"])
    for fn in (
        lambda: stage_plan("one",plan(),environment=e),
        lambda: inspect_plan("P19","one",environment=e),
        lambda: mark_intent_uncertain("P19","one","A","attempt-1",environment=e),
        lambda: has_exact_intent("P19","one","A","attempt-1"),
    ):
        with pytest.raises(ValueError,match="PERSISTED_PLAN_INTEGRITY_CONFLICT"):
            fn()


def test_upstream_runtime_is_protected_and_invalid_map_is_controlled(tmp_path):
    e=env(tmp_path)
    with pytest.raises(ValueError,match="OVERLAPS_PROTECTED_ROOT"):
        stage_plan("one",plan(),environment={**e,"PDRW_RUNTIME_DIR":e["PDRW_ORCH_RUNTIME_DIR"]})
    config=tmp_path/"config"/"map.json"
    config.parent.mkdir()
    config.write_text("[]",encoding="utf-8")
    with pytest.raises(ValueError,match="PROJECT_MAP_UNREADABLE"):
        stage_plan("one",plan(),environment={**e,"PDRW_AGENT_CONFIG":str(config)})


def test_invalid_task_id_does_not_create_store(tmp_path):
    with pytest.raises(ValueError,match="invalid task_id"):
        stage_plan("one",(TaskPacket("../bad","P19","review","Synthetic",idempotency_key="key"),),environment=env(tmp_path))
    assert not (tmp_path/"private-runtime").exists()


def test_database_hardlink_rejected(tmp_path):
    import os
    e=env(tmp_path)
    stage_plan("one",plan(),environment=e)
    try:
        os.link(tmp_path/"private-runtime"/"orchestrator.sqlite",tmp_path/"other.db")
    except OSError:
        pytest.skip("hardlink unavailable on host")
    with pytest.raises(ValueError,match="DATABASE_REDIRECTED"):
        inspect_plan("P19","one",environment=e)
