"""M4-A deterministic counterexamples; not historical efficacy data."""
import json
from pathlib import Path

import pytest

from pdrw_orchestrator.research_options import compare_options, context_digest
from pdrw_orchestrator.registry import AgentSpec
from pdrw_orchestrator.cli import main

AGENTS = (
    AgentSpec("old", "codex", ("review",), False, 1),
    AgentSpec("mock", "mock", ("review",), True, 2),
    AgentSpec("other", "claude", ("review",), True, 3),
    AgentSpec("aide", "aide", ("code_experiment",), False, 4),
)


def bundle(kind="INDEPENDENT_REVIEW", protocol="VALID"):
    return {"mode":"ADVISORY_DRAFT_ONLY", "project_id":"P","task_id":"T",
            "next_task":{"proposal_id":"N"},
            "result":{"agent_id":"old","scientific_assessment":{
                "reported_protocol_status":protocol,"reported_outcome":"NEGATIVE"}},
            "decision":{"decision_type":kind,"authorization_status":"NOT_REQUIRED_FOR_PROPOSAL"},
            "next_guidance":{}, "source_context":None}


def option(ident="one", **extra):
    return {"id":ident, "route":"MINIMAL_CHECK","premise":"Check the split",
            "evidence_refs":["original:protocol"],"discriminating_outcomes":["Pass","Fail"],
            "stop_rule":"Stop after one decisive check","capability":"review",
            "prerequisite":"SUPPORTED","scope":"EXISTING_SCOPE_DECLARED",
            "decision_value":2,"contribution_potential":2,"tokens":100,"wall_seconds":10,
            **extra}


def manifest(b, options):
    return {"schema_version":"1.0","project_id":"P","proposal_id":"N",
            "context_sha256":context_digest(b),"remaining_budget":{"tokens":500,"wall_seconds":50},
            "options":options}


def test_dominated_route_removed_and_tradeoff_retained():
    b=bundle()
    m=manifest(b,[option(),option("expensive",tokens=200),
                  option("higher_potential",contribution_potential=3,tokens=300)])
    result=compare_options(b,m,AGENTS)
    assert result["frontier_option_ids"]==["one","higher_potential"]
    assert result["selected_option_id"] is None
    assert result["recommended_agent_id"] is None
    assert result["options"][0]["declared_agent_candidates"]==[
        {"agent_id":"other","capability_declared":True,"host_ready_verified":False}]
    assert result["execution_authorized"] is False


@pytest.mark.parametrize("extra,reason",[
    ({"route":"PIVOT"},"MATERIAL_CHANGE_REQUIRES_ORIGINAL_SCOPE_REVIEW"),
    ({"route":"NARROW_CLAIM"},"MATERIAL_CHANGE_REQUIRES_ORIGINAL_SCOPE_REVIEW"),
    ({"scope":"NEW_SCOPE"},"MATERIAL_CHANGE_REQUIRES_ORIGINAL_SCOPE_REVIEW"),
    ({"scope":"UNKNOWN"},"EXISTING_SCOPE_UNVERIFIED"),
    ({"prerequisite":"UNKNOWN"},"PREMISE_UNKNOWN"),
    ({"prerequisite":"CONTRADICTED"},"PREMISE_CONTRADICTED"),
    ({"tokens":None},"RESOURCE_OR_VALUE_UNKNOWN"),
    ({"tokens":501},"DECLARED_BUDGET_EXCEEDED"),
])
def test_incomparable_routes_preserved_not_ranked(extra,reason):
    b=bundle()
    result=compare_options(b,manifest(b,[option(**extra)]),AGENTS)
    assert result["frontier_option_ids"]==[]
    assert reason in result["options"][0]["comparison_blockers"]


def test_invalid_method_precedes_more_optimization():
    b=bundle(protocol="INVALID")
    result=compare_options(b,manifest(b,[option("tune",route="CONTINUE_DEV"),
                                        option("repair",route="REPAIR_METHOD")]),AGENTS)
    assert result["frontier_option_ids"]==["repair"]
    assert "REPORTED_METHOD_INVALIDITY_REVIEW_FIRST" in result["options"][0]["comparison_blockers"]


@pytest.mark.parametrize("kind",["RECONCILE","VERIFY_EXISTING_SCOPE","HOLD","SWITCH_AGENT"])
def test_existing_blocker_never_overridden(kind):
    b=bundle(kind)
    result=compare_options(b,manifest(b,[option()]),AGENTS)
    assert not result["frontier_option_ids"]
    assert result["original_decision_preserved"] is True


def test_stale_context_and_duplicate_options_rejected():
    b=bundle()
    m=manifest(b,[option()])
    b["result"]["scientific_assessment"]["reported_outcome"]="POSITIVE"
    with pytest.raises(ValueError,match="OPTIONS_CONTEXT_MISMATCH"):
        compare_options(b,m,AGENTS)
    with pytest.raises(ValueError,match="OPTION_DUPLICATE_ID"):
        compare_options(b,manifest(b,[option(),option()]),AGENTS)


def test_cli_routes_context_and_comparison(tmp_path,capsys):
    b=bundle()
    bp=tmp_path/"handoff.json"
    bp.write_text(json.dumps(b),encoding="utf-8")
    args=["routes","--handoff",str(bp)]
    assert main(args)==0
    result=json.loads(capsys.readouterr().out)
    assert result["context_sha256"]==context_digest(b)
    mp=tmp_path/"options.json"
    mp.write_text(json.dumps(manifest(b,[option()])),encoding="utf-8")
    assert main(args+["--options",str(mp)])==0
    assert json.loads(capsys.readouterr().out)["frontier_option_ids"]==["one"]
