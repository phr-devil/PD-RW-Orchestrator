"""M3-B tests: operator-declared conditions and feedback never certify science."""
import json
from pathlib import Path

import pytest

from pdrw_orchestrator.cli import main
from pdrw_orchestrator.experience_evaluation import (
    digest, screen_lessons, feedback_candidate, evaluate_pairs,
)
from pdrw_orchestrator.models import TaskPacket
from pdrw_orchestrator.policy import Guidance

ROOT = Path(__file__).resolve().parents[1]


def lesson():
    return Guidance(id="L1:v2", level="experience", source="experience:public",
                    task_types=("review",), text="Check the anchor",
                    conditions=("Prefix-visible prediction",), evidence_refs=("C1#S1",))


def task():
    return TaskPacket(task_id="NEXT-T", project_id="P", task_type="review", objective="Review")


def context(status, *, fingerprint=None, task_id="NEXT-T"):
    _, rows=screen_lessons(task(),(lesson(),))
    return {"schema_version":"1.0","project_id":"P","task_id":task_id,
            "assessments":[{"rule_id":"L1:v2","rule_sha256":fingerprint or rows[0]["rule_sha256"],
                "conditions":[{"condition":"Prefix-visible prediction","status":status,
                               "evidence_refs":["protocol-1"] if status!="UNKNOWN" else []}]}]}


@pytest.mark.parametrize("status,expected,retained", [
    ("MATCH","DECLARED_MATCH_UNVERIFIED",True),
    ("MISMATCH","EXCLUDED_DECLARED_MISMATCH",False),
    ("UNKNOWN","REVIEW_ONLY_APPLICABILITY_UNKNOWN",True),
])
def test_conditional_advice_screen(status,expected,retained):
    rules, audit=screen_lessons(task(),(lesson(),),context(status))
    assert bool(rules)==retained
    assert audit[0]["status"]==expected
    assert audit[0]["applicability_verified"] is False


def test_stale_rule_judgment_never_excludes_new_version():
    rules,audit=screen_lessons(task(),(lesson(),),context("MISMATCH",fingerprint="a"*64))
    assert rules and audit[0]["stale_or_incomplete"]
    assert audit[0]["status"]=="REVIEW_ONLY_APPLICABILITY_UNKNOWN"
    with pytest.raises(ValueError,match="APPLICABILITY_TASK_MISMATCH"):
        screen_lessons(task(),(lesson(),),context("MATCH",task_id="OTHER"))


def handoff():
    _, rows=screen_lessons(task(),(lesson(),))
    return {"mode":"ADVISORY_DRAFT_ONLY","project_id":"P","next_task":{"proposal_id":"NEXT-T"},
            "experience_retrieval":{"selected_experience_rule_ids":["L1:v2"],
                "applicability_screen":rows,"as_of":"2026-04-01"},
            "next_guidance":{"selected_items":[{"id":"L1:v2","level":"experience"}]}}


def assessment(**extra):
    b=handoff()
    return {"schema_version":"1.0","project_id":"P","task_id":"NEXT-T",
            "rule_id":"L1:v2","rule_sha256":b["experience_retrieval"]["applicability_screen"][0]["rule_sha256"],
            "observed_at":"2026-04-02","science":"NEGATIVE","engineering":"COMPLETED",
            "transfer":"HELPFUL","usage":"APPLIED","observation":"A minimal check was decisive.",
            "evidence_refs":["run-1"],**extra}


@pytest.mark.parametrize("kwargs,outcome", [
    ({},"POSITIVE"),
    ({"transfer":"HARMFUL"},"NEGATIVE"),
    ({"transfer":"UNKNOWN"},"INCONCLUSIVE"),
    ({"science":"POSITIVE","engineering":"FAILED","transfer":"HARMFUL"},"INCONCLUSIVE"),
    ({"science":"INVALID","transfer":"HARMFUL"},"INCONCLUSIVE"),
    ({"usage":"UNKNOWN","transfer":"HARMFUL"},"INCONCLUSIVE"),
    ({"usage":"NOT_APPLIED","transfer":"HELPFUL"},"INCONCLUSIVE"),
])
def test_feedback_separates_science_engineering_and_lesson_effect(kwargs,outcome):
    result=feedback_candidate(handoff(),assessment(**kwargs))
    assert result["feedback"]["outcome"]==outcome
    assert result["feedback"]["lesson_id"]=="L1"
    assert result["negative_transfer_candidate"]==(outcome=="NEGATIVE")
    assert result["automatic_lesson_update"] is False
    assert result["actual_usage_verified"] is False


def test_feedback_rejects_wrong_version_identity_or_time():
    for extra in ({"rule_sha256":"bad"},{"task_id":"OTHER"},{"observed_at":"2026-01-01"}):
        with pytest.raises(ValueError):
            feedback_candidate(handoff(),assessment(**extra))


def pair():
    p="a"*64
    rubric={"source_legality":1,"scientific_validity":1,
            "decision_relevance":0,"avoids_redundant_work":0}
    a={"protocol_sha256":p,"result_ref":"A","reviewer_ref":"R","rubric":rubric,
       "tokens":100,"wall_seconds":5}
    b={**a,"result_ref":"B","rubric":{**rubric,"source_legality":0,
         "decision_relevance":1,"avoids_redundant_work":1},"tokens":90}
    return {"case_id":"C","protocol_sha256":p,"without_experience":a,"with_experience":b}


def test_critical_regression_not_hidden_by_aggregate_gain():
    p=pair()
    result=evaluate_pairs({"schema_version":"1.0","pairs":[p]})
    assert result["mean_quality_delta"]==1
    assert result["critical_regression_count"]==1
    assert result["negative_transfer_candidates"]==1
    assert result["total_tokens_delta"]==-10
    assert result["causal_effect_verified"] is False
    with pytest.raises(ValueError,match="PAIR_DUPLICATE_CASE"):
        evaluate_pairs({"schema_version":"1.0","pairs":[p,p]})


def test_pair_budget_protocol_must_match():
    p=pair()
    p["with_experience"]["protocol_sha256"]="b"*64
    with pytest.raises(ValueError,match="PAIR_PROTOCOL_MISMATCH"):
        evaluate_pairs({"schema_version":"1.0","pairs":[p]})


def test_feedback_and_pair_cli(tmp_path,capsys):
    paths={}
    for name,obj in (("handoff",handoff()),("assessment",assessment()),("pairs",{"schema_version":"1.0","pairs":[pair()]})):
        path=tmp_path/(name+".json")
        path.write_text(json.dumps(obj),encoding="utf-8")
        paths[name]=str(path)
    assert main(["experience","feedback","--handoff",paths["handoff"],"--assessment",paths["assessment"]])==0
    assert json.loads(capsys.readouterr().out)["status"]=="FEEDBACK_CANDIDATE_UNVERIFIED"
    assert main(["experience","evaluate","--assessment",paths["pairs"]])==0
    assert json.loads(capsys.readouterr().out)["critical_regression_count"]==1


def test_cli_screen_excludes_mismatched_advice(tmp_path,monkeypatch,capsys):
    from pdrw_orchestrator import cli
    t=ROOT/"examples/decision-task.example.json"
    r=ROOT/"examples/agent-result-v2.example.json"
    raw=json.loads(r.read_text(encoding="utf-8"))
    raw["execution"]["status"]="FAILED"
    result_path=tmp_path/"result.json"
    result_path.write_text(json.dumps(raw),encoding="utf-8")
    def fake(proposed,**kw):
        rule=Guidance(id="L1:v2",level="experience",source="experience:public",
                      task_types=(proposed.task_type,),text="Check the anchor",
                      conditions=("Prefix-visible prediction",),evidence_refs=("C1#S1",))
        return (rule,),{"status":"EXPERIENCE_ADVISORIES_RECEIVED"}
    monkeypatch.setattr(cli,"retrieve_for_task",fake)
    args=["advise","--task-file",str(t),"--result-file",str(result_path),
          "--experience-config","operator.json","--experience-query","leakage",
          "--experience-as-of","2026-04-01"]
    assert main(args)==0
    original=json.loads(capsys.readouterr().out)
    row=original["experience_retrieval"]["applicability_screen"][0]
    ctx={"schema_version":"1.0","project_id":original["project_id"],
        "task_id":original["next_task"]["proposal_id"],
        "assessments":[{"rule_id":row["rule_id"],"rule_sha256":row["rule_sha256"],
            "conditions":[{"condition":row["conditions"][0],"status":"MISMATCH","evidence_refs":["protocol"]}]}]}
    path=tmp_path/"conditions.json"
    path.write_text(json.dumps(ctx),encoding="utf-8")
    assert main(args+["--experience-applicability",str(path)])==0
    filtered=json.loads(capsys.readouterr().out)
    assert filtered["experience_retrieval"]["selected_experience_rule_ids"]==[]
    assert filtered["decision"]==original["decision"]
    assert "Check the anchor" not in filtered["agent_instruction_draft"]


def test_matched_draft_ablation_single_retrieval(tmp_path,monkeypatch,capsys):
    from pdrw_orchestrator import cli
    t=ROOT/"examples/decision-task.example.json"
    raw=json.loads((ROOT/"examples/agent-result-v2.example.json").read_text(encoding="utf-8"))
    raw["execution"]["status"]="FAILED"
    path=tmp_path/"result.json"
    path.write_text(json.dumps(raw),encoding="utf-8")
    calls=[]
    def fake(proposed,**kw):
        calls.append(proposed.task_id)
        return (Guidance(id="L1:v2",level="experience",source="experience:public",
                    task_types=(proposed.task_type,),text="Check the anchor",
                    conditions=("Prefix prediction",),evidence_refs=("C1#S1",)),),{
                    "status":"EXPERIENCE_ADVISORIES_RECEIVED"}
    monkeypatch.setattr(cli,"retrieve_for_task",fake)
    assert main(["advise","--task-file",str(t),"--result-file",str(path),
        "--experience-config","operator.json","--experience-query","leakage",
        "--experience-as-of","2026-04-01","--experience-ablation"])==0
    result=json.loads(capsys.readouterr().out)
    comparison=result["experience_ablation"]
    assert comparison["status"]=="MATCHED_DRAFTS_ONLY"
    assert len(calls)==1
    assert "Check the anchor" not in comparison["without_experience"]["instruction"]
    assert "Check the anchor" in comparison["with_experience"]["instruction"]
    assert comparison["model_calls_requested"]==0
    assert comparison["execution_authorized"] is False


def test_upstream_feedback_contract(tmp_path):
    import os
    import subprocess
    import sys
    if not os.environ.get("PDRW_EXPERIENCE_TEST_ROOT"):
        pytest.skip("actual upstream installed only in contract CI")
    packet=feedback_candidate(handoff(),assessment())
    path=tmp_path/"candidate.json"
    path.write_text(json.dumps(packet["feedback"]),encoding="utf-8")
    proc=subprocess.run([sys.executable,"-I","-B","-m","pdrw_experience.cli","feedback-check",str(path)],
                        capture_output=True,text=True,timeout=15,check=True)
    checked=json.loads(proc.stdout)
    assert checked[0]["status"]=="RECEIVED_UNVERIFIED"
    assert checked[0]["automatic_lesson_update"] is False


def test_missing_actual_usage_does_not_become_zero_cost():
    p=pair()
    p["with_experience"]["tokens"]=None
    result=evaluate_pairs({"schema_version":"1.0","pairs":[p]})
    assert result["total_tokens_delta"] is None
    assert result["token_pairs_measured_declared"]==0
    assert result["pairs"][0]["tokens_delta"] is None
    assert result["critical_regression_count"]==1
