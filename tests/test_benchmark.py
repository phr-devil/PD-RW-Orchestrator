"""Synthetic regressions; no historical efficacy or actual provider calls."""
import json
from pathlib import Path
import pytest

from pdrw_orchestrator.benchmark import replay, assess, compare_providers
from pdrw_orchestrator.experience_evaluation import digest
from pdrw_orchestrator.registry import AgentSpec
from pdrw_orchestrator.cli import main

ROOT=Path(__file__).resolve().parents[1]
T="2026-01-01T01:00:00+00:00"
SHA="a"*64
AGENTS=(AgentSpec("a","codex",("review",),False,1),
        AgentSpec("b","claude",("review",),False,2))


def case(ident,status="COMPLETED"):
    task={"project_id":"P","task_id":ident,"task_type":"code_experiment","objective":"Evaluate"}
    result={"schema_version":"2.0","project_id":"P","task_id":ident,"agent_id":"a",
            "attempt_id":"A","execution":{"status":status},"deliverables":{"run_refs":["R"]}}
    return {"case_id":ident,"cutoff":T,"input_status":"AVAILABLE","availability_refs":["original-freeze"],
            "inputs":{"task":task,"result":result,"source_context":None,
                      "available_at":{"task":T,"result":T,"source_context":None}}}


def cohort():
    return {"schema_version":"1.0","reference_commitment_sha256":None,"cases":[case("positive"),case("failed","FAILED"),
        {**case("missing"),"input_status":"UNAVAILABLE","inputs":None}]}


def test_replay_actual_decision_engine_and_full_cohort():
    result=replay(cohort(),(),AGENTS)
    assert [r["decision_type"] for r in result["cases"]]==["INDEPENDENT_REVIEW","REVISE_PLAN",None]
    assert result["historical_availability_verified"] is False
    ref={"schema_version":"1.0","replay_sha256":digest(result),"cases":[
        {"case_id":r["case_id"],"case_sha256":r["case_sha256"],"reference_status":"REVIEWED_DECLARED",
         "acceptable_decisions":["INDEPENDENT_REVIEW"],"evidence_refs":["later-review"]}
        for r in result["cases"]]}
    score=assess(result,ref)
    assert score["assessed_count"]==2 and score["cohort_count"]==3
    assert score["match_count"]==1 and score["match_rate_assessed"]==0.5
    assert score["cases"][-1]["status"]=="INPUT_UNAVAILABLE"
    ref["cases"].pop()
    with pytest.raises(ValueError,match="COHORT_MISMATCH"):
        assess(result,ref)


def test_future_and_naive_timestamps_block_replay():
    m=cohort()
    m["cases"][0]["inputs"]["available_at"]["result"]="2026-01-01T03:00:00+01:00"
    with pytest.raises(ValueError,match="FUTURE_INPUT"):
        replay(m,(),AGENTS)
    m["cases"][0]["inputs"]["available_at"]["result"]="2026-01-01T01:00:00"
    with pytest.raises(ValueError,match="NEEDS_OFFSET"):
        replay(m,(),AGENTS)


def test_unknown_reference_not_failure_and_replay_binding():
    result=replay({"schema_version":"1.0","reference_commitment_sha256":None,"cases":[case("one")]},(),AGENTS)
    ref={"schema_version":"1.0","replay_sha256":digest(result),"cases":[{
        "case_id":"one","case_sha256":result["cases"][0]["case_sha256"],
        "reference_status":"UNKNOWN","acceptable_decisions":[],"evidence_refs":["missing-review"]}]}
    assert assess(result,ref)["match_rate_assessed"] is None
    result["engine_version"]="changed"
    with pytest.raises(ValueError,match="REPLAY_BINDING_MISMATCH"):
        assess(result,ref)


def providers():
    p=[{"agent_id":x,"version":"v1","config_sha256":SHA} for x in ("a","b")]
    arms=[{"agent_id":x["agent_id"],"provider_sha256":digest(x),"protocol_sha256":SHA,
           "status":"COMPLETED","result_ref":"result-"+x["agent_id"],"reviewer_ref":"review",
           "rubric":{"source_legality":1,"scientific_validity":1,"decision_relevance":1,"avoids_redundant_work":0},
           "tokens":100,"wall_seconds":10} for x in p]
    return {"schema_version":"1.0","capability":"review","providers":p,"cases":[
        {"case_id":"one","protocol_sha256":SHA,"budget":{"tokens":200,"wall_seconds":30},"arms":arms}]}


def test_provider_critical_regression_and_budget():
    m=providers()
    b=m["cases"][0]["arms"][1]
    b["rubric"]["scientific_validity"]=0
    b["rubric"]["avoids_redundant_work"]=1
    b["tokens"]=50
    result=compare_providers(m,AGENTS)
    assert result["critical_regression_count"]==1 and result["paired_rubric_count"]==1
    assert result["routing_priority_changed"] is False
    b["tokens"]=201
    result=compare_providers(m,AGENTS)
    assert result["paired_rubric_count"]==0 and result["pairs"][0]["budget_exceeded_declared"]==["b"]


def test_failed_unknown_cost_kept_in_provider_denominator():
    m=providers()
    b=m["cases"][0]["arms"][1]
    b.update(status="FAILED",rubric=None,reviewer_ref=None,tokens=None)
    result=compare_providers(m,AGENTS)
    assert result["cohort_count"]==1 and result["paired_rubric_count"]==0
    assert result["completion_counts"]=={"a":1,"b":0}
    assert result["pairs"][0]["tokens_delta"] is None


@pytest.mark.parametrize("field,value",[("provider_sha256","b"*64),("protocol_sha256","b"*64)])
def test_provider_pair_must_match(field,value):
    m=providers()
    m["cases"][0]["arms"][1][field]=value
    with pytest.raises(ValueError,match="PAIR_BINDING_MISMATCH"):
        compare_providers(m,AGENTS)


def test_benchmark_cli_replay(tmp_path,capsys):
    p=tmp_path/"cases.json"
    p.write_text(json.dumps(cohort()),encoding="utf-8")
    assert main(["benchmark","replay","--manifest",str(p)])==0
    assert json.loads(capsys.readouterr().out)["cases"][0]["decision_type"]=="INDEPENDENT_REVIEW"


def test_reference_commitment_cannot_change_after_replay():
    m=cohort()
    refs=[{"case_id":r["case_id"],"case_sha256":digest(r),
           "reference_status":"REVIEWED_DECLARED","acceptable_decisions":["INDEPENDENT_REVIEW"],
           "evidence_refs":["review-ref"]} for r in m["cases"]]
    m["reference_commitment_sha256"]=digest(refs)
    result=replay(m,(),AGENTS)
    ref={"schema_version":"1.0","replay_sha256":digest(result),"cases":refs}
    assert assess(result,ref)["reference_commitment_matched"] is True
    refs[0]["acceptable_decisions"]=["HOLD"]
    with pytest.raises(ValueError,match="REFERENCE_COMMITMENT_MISMATCH"):
        assess(result,ref)


def test_unknown_budget_never_counts_as_matched_budget_quality():
    m=providers()
    m["cases"][0]["arms"][1]["tokens"]=None
    result=compare_providers(m,AGENTS)
    assert result["paired_rubric_count"]==1
    assert result["within_budget_paired_rubric_count"]==0
    assert result["pairs"][0]["budget_unknown"]==["b"]
