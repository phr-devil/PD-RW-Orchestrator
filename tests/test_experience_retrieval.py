"""Bounded local Experience integration; no ACE or external model calls."""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from pdrw_orchestrator.integrations import experience
from pdrw_orchestrator.models import TaskPacket
from pdrw_orchestrator.policy import Guidance, compile_guidance
from pdrw_orchestrator.cli import main

ROOT = Path(__file__).resolve().parents[1]


def write_json(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")


def config(tmp_path):
    source = tmp_path / "sources"
    source.mkdir()
    settings = {"schema_version":"1.0", "python":sys.executable, "source_root":str(source)}
    for key in ("lessons","cases","receipts","source_index","trusted_public_key"):
        path = tmp_path / key
        path.write_bytes(b"synthetic")
        settings[key] = str(path)
    settings["public_key_sha256"] = hashlib.sha256(b"synthetic").hexdigest()
    p = tmp_path / "config.json"
    write_json(p, settings)
    return p, settings


def task(kind="review"):
    return TaskPacket(project_id="P",task_id="T",task_type=kind,objective="Review evaluation")


def item(ident="z",kind="review",**extra):
    return {"id":ident, "level":"experience", "source":"PD-RW-Experience:L1:attested_review:review-1",
            "text":"Check leakage", "task_types":[kind], "evidence_refs":["CASE#SOURCE"],
            "conditions":["Prefix prediction"], **extra}


def invoke(path,kind="review"):
    return experience.retrieve_for_task(task(kind),config_path=path,query="leakage",as_of="2026-04-01")


def test_retrieval_uses_one_readonly_call_and_preserves_rank(tmp_path,monkeypatch):
    p,_ = config(tmp_path)
    calls=[]
    def fake(argv,**kw):
        calls.append(argv)
        assert argv[1:3]==["-I","-B"]
        assert "retrieve" in argv and "--as-of=2026-04-01" in argv
        assert "--query=leakage" in argv and "--limit" in argv
        assert kw["stderr"]==subprocess.DEVNULL
        kw["stdout"].write(json.dumps([item("z"),item("a")]).encode())
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(experience.subprocess,"run",fake)
    rules,meta=invoke(p)
    assert len(calls)==1
    assert meta["status"]=="EXPERIENCE_ADVISORIES_RECEIVED"
    assert meta["model_calls_requested"]==0 and meta["permission_granted"] is False
    assert meta["provider_attestation_independently_verified"] is False
    mandatory=Guidance(id="mandatory",level="requirement",source="local",task_types=("review",),text="Keep original scope")
    packet=compile_guidance(task(),(mandatory,)+rules,limit=2)
    assert packet.rule_ids==("mandatory","z")
    assert packet.selected_items[1]["conditions"]==["Prefix prediction"]
    assert packet.selected_items[1]["evidence_refs"]==["CASE#SOURCE"]


@pytest.mark.parametrize("rows", [
    [item(level="requirement")], [item(kind="analysis")],
    [item(evidence_refs=[])], [item(),item()],
    [item(source="self-asserted")], [item(deny_effects=["upload"])],
])
def test_untrusted_or_mismatched_provider_rows_rejected(tmp_path,monkeypatch,rows):
    p,_=config(tmp_path)
    def fake(argv,**kw):
        kw["stdout"].write(json.dumps(rows).encode())
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(experience.subprocess,"run",fake)
    rules,meta=invoke(p)
    assert not rules and meta["status"]=="EXPERIENCE_REQUEST_OR_RESPONSE_REJECTED"
    assert meta["permission_granted"] is False


def test_pin_mismatch_does_not_launch_provider(tmp_path,monkeypatch):
    p,cfg=config(tmp_path)
    Path(cfg["trusted_public_key"]).write_bytes(b"replacement")
    monkeypatch.setattr(experience.subprocess,"run",lambda *a,**k:pytest.fail("must not call"))
    rules,meta=invoke(p)
    assert not rules and meta["status"]=="EXPERIENCE_REQUEST_OR_RESPONSE_REJECTED"


def test_catalog_drift_and_timeout_distinct_from_no_match(tmp_path,monkeypatch):
    p,cfg=config(tmp_path)
    def mutate(argv,**kw):
        Path(cfg["lessons"]).write_bytes(b"changed")
        kw["stdout"].write(b"[]")
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(experience.subprocess,"run",mutate)
    assert invoke(p)[1]["status"]=="EXPERIENCE_INPUT_CHANGED"
    def timeout(*a,**kw):
        raise subprocess.TimeoutExpired("synthetic",30)
    monkeypatch.setattr(experience.subprocess,"run",timeout)
    assert invoke(p)[1]["status"]=="EXPERIENCE_TIMEOUT_NO_RETRY"


def test_cli_integrates_only_next_task_and_reports_conditions(tmp_path,monkeypatch,capsys):
    from pdrw_orchestrator import cli
    base=ROOT/"examples"
    task_file=base/"decision-task.example.json"
    result_file=base/"agent-result-v2.example.json"
    result=json.loads(result_file.read_text(encoding="utf-8"))
    result["execution"]["status"]="FAILED"
    path=tmp_path/"result.json"
    write_json(path,result)
    calls=[]
    def fake(t,**kw):
        calls.append(t.task_type)
        return experience.accept_advisories([item(kind=t.task_type)]), {
            "status":"EXPERIENCE_ADVISORIES_RECEIVED","permission_granted":False}
    monkeypatch.setattr(cli,"retrieve_for_task",fake)
    args=["advise","--task-file",str(task_file),"--result-file",str(path),
          "--experience-config","operator.json","--experience-query","leakage",
          "--experience-as-of","2026-04-01"]
    assert main(args)==0
    obj=json.loads(capsys.readouterr().out)
    assert calls==["experiment_design"]
    assert obj["experience_retrieval"]["selected_experience_rule_ids"]==["z"]
    assert "z" not in obj["guidance"]["rule_ids"]
    assert "Prefix prediction" in obj["agent_instruction_draft"]
    assert "CASE#SOURCE" in obj["chatgpt_handoff_md"]
    assert obj["decision"]["can_auto_dispatch"] is False
    result["execution"]["status"]="BLOCKED_AUTH"
    write_json(path,result)
    assert main(args)==0
    obj=json.loads(capsys.readouterr().out)
    assert calls==["experiment_design"]
    assert obj["experience_retrieval"]["status"]=="EXPERIENCE_SKIPPED_NON_RESEARCH_NEXT_ACTION"


@pytest.mark.skipif(not os.environ.get("PDRW_EXPERIENCE_TEST_ROOT"),reason="pinned upstream installed in contract CI")
def test_actual_pinned_experience_signed_source_and_visibility(tmp_path):
    """Actual installed upstream CLI: signed public lesson, cutoff, invalid bytes."""
    import base64
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    upstream=Path(os.environ["PDRW_EXPERIENCE_TEST_ROOT"])
    case=json.loads((upstream/"examples/case.synthetic.json").read_text(encoding="utf-8"))
    lesson=json.loads((upstream/"examples/lesson.synthetic.json").read_text(encoding="utf-8"))
    p,cfg=config(tmp_path)
    source=Path(cfg["source_root"])/"original.txt"
    source.write_bytes(b"public synthetic evidence")
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    case["source_refs"][0]["sha256"]=digest
    lesson["case_refs"][0]["sha256"]=digest
    def canonical(obj):
        return json.dumps(obj,sort_keys=True,ensure_ascii=False,separators=(",",":"),allow_nan=False).encode("utf-8")
    key=Ed25519PrivateKey.generate()
    public=key.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo)
    payload={"schema_version":"1.0","kind":"LESSON_REVIEW",
             "subject_sha256":hashlib.sha256(canonical(lesson)).hexdigest(),
             "reviewed_at":lesson["available_at"],"decision":"APPROVED_FOR_ADVISORY"}
    receipt={"payload":payload,"signature":base64.b64encode(key.sign(canonical(payload))).decode("ascii")}
    write_json(Path(cfg["lessons"]),[lesson])
    write_json(Path(cfg["cases"]),[case])
    write_json(Path(cfg["receipts"]),{lesson["lesson_id"]:receipt})
    write_json(Path(cfg["source_index"]),{case["case_id"]:{case["source_refs"][0]["source_id"]:"original.txt"}})
    Path(cfg["trusted_public_key"]).write_bytes(public)
    cfg["public_key_sha256"]=hashlib.sha256(public).hexdigest()
    write_json(p,cfg)
    rules,meta=invoke(p,"experiment_design")
    assert meta["status"]=="EXPERIENCE_ADVISORIES_RECEIVED",meta
    assert len(rules)==1 and rules[0].level=="experience"
    assert rules[0].conditions and rules[0].evidence_refs
    rules,meta=experience.retrieve_for_task(task("experiment_design"),config_path=p,
                    query="leakage",as_of="2026-01-01")
    assert not rules and meta["status"]=="EXPERIENCE_NO_MATCH"
    source.write_bytes(b"tampered source")
    rules,meta=invoke(p,"experiment_design")
    assert not rules and meta["status"]=="EXPERIENCE_NO_MATCH"
