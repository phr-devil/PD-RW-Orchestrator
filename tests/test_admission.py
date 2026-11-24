"""Read-only admission adapter regressions; real upstream test in contract CI."""
import hashlib
import json
import sys
from types import SimpleNamespace

import pytest

from pdrw_orchestrator.integrations import admission
from pdrw_orchestrator.cli import main


def proposal():
    return {"schema_version":"pdrw-dev-plan-v1","project_id":"P1","operation_id":"O1",
            "task_id":"T1","runner_id":"R1","action":"DEV_CODE",
            "task_spec_sha256":"a"*64,"code_sha256":"b"*64,"dataset_manifest_sha256":"c"*64,
            "time_limit_seconds":60,"cpu_limit":1,"gpu_count":0,"network":False,"data_split":"dev"}


@pytest.mark.parametrize("change,expected",[
    ({},"DEV_ADMISSION_PREVIEW_ONLY"),
    ({"execution_authorized":True},"DEV_ADMISSION_RESPONSE_CONFLICT"),
    ({"task_id":"other"},"DEV_ADMISSION_RESPONSE_CONFLICT"),
    ({"plan_sha256":"other"},"DEV_ADMISSION_RESPONSE_CONFLICT"),
    ({"original_user_grant_verified":True},"DEV_ADMISSION_RESPONSE_CONFLICT"),
    ({"status":"READY"},"DEV_ADMISSION_RESPONSE_CONFLICT"),
])
def test_preview_never_grants_or_dispatches(monkeypatch,change,expected):
    monkeypatch.setattr(admission,"_source_settings",lambda *a:({"registry_sha256_local_only":"a"*64},None))
    def fake(argv,**kw):
        assert argv[1:4]==["-I","-B","-c"]
        raw=kw["stdin"].read()
        assert json.loads(raw)==proposal()
        response={k:proposal()[k] for k in (*admission._IDS,"action")}
        response.update({k:False for k in admission._FALSE})
        response.update(plan_sha256=hashlib.sha256(raw).hexdigest(),
            authorization_state="UNVERIFIED",runtime_state="UNSTARTED",evidence_state="NOT_REVIEWED",
            science_state="NOT_REVIEWED",status="TRUSTED_HOST_NOT_CONNECTED",
            project_machine_readiness="MACHINE_METADATA_READY")
        response.update(change)
        kw["stdout"].write(json.dumps(response).encode())
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(admission.subprocess,"run",fake)
    out=admission.preview_admission(proposal(),python_executable=sys.executable)
    assert out["status"]==expected
    assert out["execution_authorized"] is False
    assert out["new_author_grant_required"] is None


def test_doctor_and_invalid_plan_no_write(tmp_path,monkeypatch,capsys):
    runtime=tmp_path/"runtime"
    monkeypatch.setenv("PDRW_ORCH_RUNTIME_DIR",str(runtime))
    from pdrw_orchestrator import cli
    monkeypatch.setattr(cli,"audit_host",lambda *a,**k:{"status":"HOST_READ_ONLY_CHECKS_COMPLETE"})
    assert main(["doctor","--project-id","P1"])==0
    assert json.loads(capsys.readouterr().out)["execution_authorized"] is False
    assert not runtime.exists()
    plan=tmp_path/"bad.json"
    plan.write_text("{}",encoding="utf-8")
    assert main(["host","admission","--plan-file",str(plan)])==3
    assert json.loads(capsys.readouterr().out)["status"]=="DEV_PROPOSAL_ENVELOPE_INVALID"
