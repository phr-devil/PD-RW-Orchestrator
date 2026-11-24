"""Actual upstream CLI and original core writer on isolated synthetic sources."""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from pdrw_orchestrator.integrations.pdrw import inspect_resume
from pdrw_orchestrator.integrations.source_checks import inspect_source_chain

pytestmark=pytest.mark.skipif(not os.getenv("PDRW_ORCH_TEST_RULE_ROOT"),
                             reason="pinned upstream contract CI only")


def test_actual_registered_run_and_receipt(tmp_path,monkeypatch):
    from pdrw_agent.config import Settings
    from pdrw_agent.service import ResearchService
    rules=Path(os.environ["PDRW_ORCH_TEST_RULE_ROOT"]).resolve()
    root=tmp_path/"project"
    root.mkdir()
    (root/"runs").mkdir()
    (root/"RESEARCH_RECORD.md").write_text("## 0. Snapshot\nPRIVATE_SYNTHETIC_MARKER\n## 1. History\n",encoding="utf-8")
    (root/"PAPER_BLUEPRINT.md").write_text("Synthetic",encoding="utf-8")
    def core(*args):
        p=subprocess.run([sys.executable,"-m","core.cli",*args],
                         cwd=rules,capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=20)
        assert p.returncode==0,p.stderr
    core("init","--root",str(root),"--project-id","synthetic-original")
    refs={"metrics":"runs/metrics.json","predictions":"runs/predictions.csv","code":"runs/code.py"}
    for key,path in refs.items():
        (root/path).write_text({"metrics":'{"MAE":0.1}',"predictions":"y_true,y_pred\n1,1.1\n","code":"pass\n"}[key],encoding="utf-8")
    run={"run_id":"RUN1","task_id":"T1","protocol_id":"PROTO-v1",
         "dataset_version":"synthetic-v1","evaluator_version":"eval-v1",
         "group_split":"group-disjoint","sample_ids_hash":"synthetic-ids",
         "status":"VALID","split":"dev","legal_inputs":["sensor"],
         "metrics":{"MAE":0.1},"artifact_refs":refs}
    (root/"runs/run.json").write_text(json.dumps(run),encoding="utf-8")
    core("record","--root",str(root),"--kind","run","--artifact","runs/run.json")
    config=tmp_path/"map.json"
    config.write_text(json.dumps({"schema_version":1,"projects":{"P1":{
        "root":str(root),"expected_state_project_id":"synthetic-original"}}}),encoding="utf-8")
    monkeypatch.setenv("PDRW_AGENT_CONFIG",str(config))
    monkeypatch.setenv("PDRW_WORKFLOW_ROOT",str(rules))
    monkeypatch.setenv("PDRW_RUNTIME_DIR",str(tmp_path/"upstream-runtime"))
    svc=ResearchService(Settings.load(str(config),str(rules)))
    out=svc.call("begin_operation_receipt",project_id="P1",operation_id="OP1",task_id="T1",action="DEV_CODE")
    assert out["status"]=="RECEIPT_CREATED",out
    out=svc.call("checkpoint_operation_receipt",project_id="P1",operation_id="OP1",
                 expected_revision=0,phase="ARTIFACT_REPORTED",artifact_ref="runs/run.json")
    assert out["status"]=="CHECKPOINT_SAVED",out
    def snapshot():
        return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()
                for p in root.rglob("*") if p.is_file()}
    before=snapshot()
    resume=inspect_resume("P1",python_executable=sys.executable)
    assert resume["source_status"]=="ARTIFACT_REVIEW_PENDING",resume
    assert resume["latest_valid_run_id_declared"]=="RUN1",resume
    assert resume["independent_permitted_read_only_review_hint"] is True
    checked=inspect_source_chain("P1",operation_id="OP1",run_id="RUN1",python_executable=sys.executable)
    assert checked["verification_status"]=="SOURCE_READ_ONLY_CHECKS_COMPLETE",checked
    assert checked["run"]["bytes_consistent"] is True
    assert checked["run"]["protocol_id_declared"]=="PROTO-v1"
    assert checked["cross_reference_status"]=="TASK_ID_DECLARATIONS_MATCH_ONLY"
    assert checked["operation"]["recovery_class"]=="PENDING_SCIENTIFIC_REVIEW"
    assert checked["author_scope_verified"] is False
    assert checked["scientific_validity_verified"] is False
    assert checked["restart_permitted"] is False
    assert "PRIVATE_SYNTHETIC_MARKER" not in json.dumps(checked)
    assert snapshot()==before
    (root/refs["predictions"]).write_text("changed",encoding="utf-8")
    changed=inspect_source_chain("P1",run_id="RUN1",python_executable=sys.executable)
    assert changed["verification_status"]=="SOURCE_RECONCILIATION_REQUIRED",changed
    assert changed["run"]["status"]=="RUN_LINK_HASH_MISMATCH",changed
    assert changed["restart_permitted"] is False
