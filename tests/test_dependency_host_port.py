"""An in-process host port can supply upstream evidence refs, never a permit."""
import hashlib
import json
import sqlite3

import pytest
from pdrw_orchestrator.models import TaskPacket
from pdrw_orchestrator.runtime.dependencies import DependencyEvidence
from pdrw_orchestrator.runtime.store import inspect_plan, mark_intent_uncertain, stage_plan

def original_plan():
    return (
        TaskPacket(task_id="DISCOVERY", project_id="P", task_type="discovery",
                   objective="synthetic", idempotency_key="discovery-1"),
        TaskPacket(task_id="REVIEW", project_id="P", task_type="review",
                   objective="synthetic review", dependencies=("DISCOVERY",),
                   idempotency_key="review-1"),
    )

def test_dependent_task_requires_host_review_and_does_not_dispatch(tmp_path):
    e={"PDRW_ORCH_RUNTIME_DIR":str(tmp_path/"state")}
    stage_plan("plan", original_plan(), environment=e)
    class HostStub:
        def verify_dependencies(self, project_id, plan_id, task_id, upstream_task_ids):
            assert (project_id,plan_id,task_id,upstream_task_ids)==("P","plan","REVIEW",("DISCOVERY",))
            return (DependencyEvidence("DISCOVERY","project-receipt:0001",hashlib.sha256(b"synthetic").hexdigest()),)
    result=mark_intent_uncertain("P","plan","REVIEW","attempt-1",environment=e,
                                 dependency_reviewer=HostStub())
    assert result["status"]=="INTENT_UNCERTAIN_NO_DISPATCH"
    assert result["dispatch_performed"] is False
    assert result["execution_authorized"] is False
    assert inspect_plan("P","plan",environment=e)["status"]=="RECONCILIATION_REQUIRED"
    with sqlite3.connect(tmp_path/"state"/"orchestrator.sqlite") as db:
        row=db.execute("SELECT dependency_review_refs FROM tasks WHERE task_id='REVIEW'").fetchone()[0]
    assert json.loads(row)[0]["original_receipt_ref"]=="project-receipt:0001"

@pytest.mark.parametrize("payload", [(),("not a receipt",),])
def test_invalid_host_review_cannot_release_dependency(tmp_path,payload):
    e={"PDRW_ORCH_RUNTIME_DIR":str(tmp_path/"state")}
    stage_plan("plan",original_plan(),environment=e)
    class Incomplete:
        def verify_dependencies(self, *args):
            return payload
    with pytest.raises(ValueError,match="HOST_DEPENDENCY_REVIEW"):
        mark_intent_uncertain("P","plan","REVIEW","attempt-1",environment=e,
                              dependency_reviewer=Incomplete())
    assert inspect_plan("P","plan",environment=e)["uncertain_intent_count"]==0

def test_cli_cannot_inject_fake_host_port(tmp_path):
    from pdrw_orchestrator.cli import main
    import pytest
    e={"PDRW_ORCH_RUNTIME_DIR":str(tmp_path/"state")}
    stage_plan("plan",original_plan(),environment=e)
    # The CLI only exposes a bounded mark-uncertain path, never a --verified flag.
    import os
    old=os.environ.get("PDRW_ORCH_RUNTIME_DIR")
    os.environ["PDRW_ORCH_RUNTIME_DIR"]=e["PDRW_ORCH_RUNTIME_DIR"]
    try:
        assert main(["schedule","mark-uncertain","--project-id","P","--plan-id","plan",
                     "--task-id","REVIEW","--attempt-id","attempt-1"])==2
    finally:
        if old is None:os.environ.pop("PDRW_ORCH_RUNTIME_DIR",None)
        else:os.environ["PDRW_ORCH_RUNTIME_DIR"]=old
    assert inspect_plan("P","plan",environment=e)["uncertain_intent_count"]==0

def test_previously_created_store_migrates_without_overwriting(tmp_path):
    folder=tmp_path/"state";folder.mkdir()
    old_path=folder/"orchestrator.sqlite"
    with sqlite3.connect(old_path) as db:
        db.execute("CREATE TABLE tasks(project_id TEXT,plan_id TEXT,task_id TEXT,digest TEXT,packet_json TEXT,phase TEXT,intent_id TEXT,updated_at TEXT,PRIMARY KEY(project_id,plan_id,task_id))")
        db.execute("CREATE TABLE plans(project_id TEXT,plan_id TEXT,digest TEXT,created_at TEXT,PRIMARY KEY(project_id,plan_id))")
        db.commit()
    e={"PDRW_ORCH_RUNTIME_DIR":str(folder)}
    stage_plan("plan", original_plan(), environment=e)
    with sqlite3.connect(old_path) as db:
        cols={r[1] for r in db.execute("PRAGMA table_info(tasks)")}
        assert "dependency_review_refs" in cols
        assert db.execute("SELECT count(*) FROM tasks").fetchone()[0]==2
