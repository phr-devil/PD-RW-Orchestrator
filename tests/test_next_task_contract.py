"""Next-task handoff contracts do not grant permissions or reuse a previous objective."""
import json
from pathlib import Path
import pytest
from jsonschema import validate

from pdrw_orchestrator.agent_result import normalize_result
from pdrw_orchestrator.cli import main
from pdrw_orchestrator.decision import decide_next
from pdrw_orchestrator.instruction import build_bundle
from pdrw_orchestrator.models import TaskPacket
from pdrw_orchestrator.next_task import policy_task_for_proposal
from pdrw_orchestrator.policy import Guidance, compile_guidance
from pdrw_orchestrator.registry import load_agents

ROOT = Path(__file__).resolve().parents[1]
AGENTS = load_agents(ROOT / "configs/agents.example.yaml")

def _task(**extra):
    return TaskPacket(task_id="T", project_id="P", task_type="code_experiment",
                      objective="Train another network", budget={"max_model_calls": 9},
                      required_effects=("local_dev_execution",),
                      authorization_refs=("H6-original",), idempotency_key="original-id",
                      **extra)

def _normalized(t):
    return normalize_result({
        "schema_version": "2.0", "project_id": "P", "task_id": "T", "agent_id": "aide",
        "attempt_id": "attempt-1", "execution": {"status": "COMPLETED"},
        "deliverables": {"run_refs": ["unverified-run-01"]},
        "scientific_assessment": {"claim_status": "VALID"},
    }, t)

def test_effects_and_old_objective_never_transferred():
    t = _task()
    n = _normalized(t)
    d = decide_next(t, n, compile_guidance(t, ()), AGENTS)
    p = d["next_task"]
    assert d["decision_type"] == "VERIFY_EXISTING_SCOPE"
    assert d["authorization_status"] == "SCOPE_NOT_YET_VERIFIED"
    assert p["task_type"] == "scope_review"
    assert p["required_effects"] == [] and p["budget"] == {}
    assert p["prior_effects_for_scope_review_only"] == ["local_dev_execution"]
    assert p["prior_authorization_refs_unverified"] == ["H6-original"]
    assert p["objective"] != t.objective
    assert p["can_dispatch"] is False

def test_completed_dev_to_independent_review_has_own_policy_and_objective():
    t = TaskPacket(task_id="T", project_id="P", task_type="code_experiment",
                   objective="Optimize parameter alpha", idempotency_key="id")
    n = _normalized(t)
    rules = (
        Guidance(id="DEV-ONLY", level="must_consider", source="user_example",
                 task_types=("code_experiment",), text="Improve model"),
        Guidance(id="REVIEW-ONLY", level="must_consider", source="user_example",
                 task_types=("review",), text="Inspect holdout leakage"),
    )
    previous = compile_guidance(t, rules)
    d = decide_next(t, n, previous, AGENTS)
    p = d["next_task"]
    assert d["decision_type"] == "INDEPENDENT_REVIEW"
    assert p["task_type"] == "review"
    assert p["objective"] != t.objective
    assert "Train" not in p["objective"]
    next_guidance = compile_guidance(policy_task_for_proposal(p), rules)
    assert next_guidance.rule_ids == ("REVIEW-ONLY",)
    bundle = build_bundle(t, n, d, previous, next_guidance=next_guidance)
    assert "REVIEW-ONLY" in bundle["agent_instruction_draft"]
    assert "DEV-ONLY" not in bundle["agent_instruction_draft"]
    assert 'NEXT task objective:' in bundle["agent_instruction_draft"]
    assert 'Next-task requested effects: []' in bundle["agent_instruction_draft"]
    assert 'Next-task budget (NOT inherited): {}' in bundle["agent_instruction_draft"]
    assert bundle["next_task"] == d["next_task"]
    for key in ("next_task",):
        validate(instance=bundle[key], schema=json.loads((ROOT / "schemas/next-task.schema.json").read_text()))

def test_untrusted_source_cannot_claim_existing_authorization():
    t = _task()
    n = _normalized(t)
    source = {
        "project_id": "P", "bridge_status": "SOURCE_REVIEW_ONLY",
        "source_status": "SOURCE_REVIEW_REQUIRED",
        "authorization_verified": True, "execution_authorized": True,
        "restart_permitted": True,
    }
    d = decide_next(t, n, compile_guidance(t, ()), AGENTS, source_context=source)
    assert d["decision_type"] == "VERIFY_EXISTING_SCOPE"
    assert d["execution_authorized"] is False
    assert d["author_decision_required_for_effects"] is False

@pytest.mark.parametrize("source_status,expected", [
    ("NEEDS_OPERATIONAL_RECONCILIATION", "RECONCILE"),
    ("NEEDS_RECONCILIATION", "RECONCILE"),
    ("BLOCKED_IDENTITY_UNKNOWN", "RECONCILE"),
    ("ARTIFACT_REVIEW_PENDING", "INDEPENDENT_REVIEW"),
    ("SOURCE_REVIEW_REQUIRED", "VERIFY_EXISTING_SCOPE"),
])
def test_real_source_state_decision_mappings(source_status, expected):
    t=_task()
    d=decide_next(t,_normalized(t),compile_guidance(t,()),AGENTS,
                  source_context={"bridge_status":"SOURCE_REVIEW_ONLY","project_id":"P",
                                  "source_status":source_status})
    assert d["decision_type"] == expected
    assert d["can_auto_dispatch"] is False

def test_cli_optin_readonly_bridge_passes_status(monkeypatch, capsys):
    from pdrw_orchestrator import cli
    observed=[]
    def inspect(project_id, **kwargs):
        observed.append(project_id)
        return {"bridge_status":"SOURCE_REVIEW_ONLY", "project_id":project_id,
                "source_status":"ARTIFACT_REVIEW_PENDING",
                "pending_scientific_review_count":1,
                "authorization_verified":False}
    monkeypatch.setattr(cli, "inspect_resume", inspect)
    args=["advise", "--task-file", str(ROOT/"examples/decision-task.example.json"),
          "--result-file", str(ROOT/"examples/agent-result-v2.example.json"), "--with-pdrw"]
    assert main(args)==0
    output=json.loads(capsys.readouterr().out)
    assert observed==["EXAMPLE"]
    assert output["decision"]["decision_type"]=="INDEPENDENT_REVIEW"
    assert output["source_context"]["source_status"]=="ARTIFACT_REVIEW_PENDING"
    assert output["next_task"]["required_effects"]==[]
    assert output["dispatch_performed"] is False

def test_readonly_optin_not_default(monkeypatch, capsys):
    from pdrw_orchestrator import cli
    monkeypatch.setattr(cli, "inspect_resume", lambda *a, **kw: (_ for _ in ()).throw(AssertionError("should not run")))
    args=["advise", "--task-file", str(ROOT/"examples/decision-task.example.json"),
          "--result-file", str(ROOT/"examples/agent-result-v2.example.json")]
    assert main(args)==0
    assert json.loads(capsys.readouterr().out)["source_context"] is None
