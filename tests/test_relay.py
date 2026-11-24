"""Scoped two-provider relay acceptance with real OS children, no paid models."""
import json
import sys
from pathlib import Path

import pytest

from pdrw_orchestrator.adapters import claude
from pdrw_orchestrator.runtime import relay
from pdrw_orchestrator.runtime.codex_pilot import pilot_task
from pdrw_orchestrator.runtime.lifecycle import PilotLifecycle, run_tracked_child
from pdrw_orchestrator.runtime.store import stage_plan, mark_intent_uncertain, has_exact_intent
from pdrw_orchestrator.contracts import compile_pilot_contract, contract_sha256
from pdrw_orchestrator.policy import load_policy, compile_guidance
from pdrw_orchestrator.host_evidence import write_pilot_contract, write_pilot_receipt

ROOT = Path(__file__).resolve().parents[1]
OPTIONS = {"policy_path": ROOT / "policies/user/research-guidance.example.yaml",
           "registry_path": ROOT / "configs/agents.example.yaml"}
REPORT = {"summary": "synthetic review",
          "observations": [{"claim": "UNTRUSTED_PRIVATE_TEXT_NOT_TO_SEND",
                            "source_refs": ["sensor_example.py:7-10", "../private.txt:1",
                                            "sensor_example.py:999"],
                            "limitations": ["UNTRUSTED_LIMITATION"]}],
          "limitations": [], "next_actions": []}


@pytest.fixture
def parent(tmp_path, monkeypatch):
    root = tmp_path / "private"
    monkeypatch.setenv("PDRW_ORCH_RUNTIME_DIR", str(root))
    task = pilot_task()
    stage_plan("parent", (task,))
    mark_intent_uncertain("PILOT", "parent", task.task_id, "first")
    directory = root / "codex-pilot" / "parent" / "first"
    directory.mkdir(parents=True)
    contract = compile_pilot_contract(task, compile_guidance(task, load_policy(OPTIONS["policy_path"])))
    write_pilot_contract(directory, contract)
    lifecycle = PilotLifecycle(directory, plan_id="parent", attempt_id="first",
                               contract_sha256=contract_sha256(contract))
    # Real local child creates the synthetic report, not an actual Codex model.
    output = directory / "codex-final.json"
    script = "import pathlib,sys; pathlib.Path(sys.argv[1]).write_text(sys.stdin.read(),encoding='utf-8')"
    code, failure = run_tracked_child([sys.executable, "-I", "-c", script, str(output)],
                                     json.dumps(REPORT), 10, lifecycle)
    assert (code, failure) == (0, None)
    write_pilot_receipt(directory, contract=contract, project_id="PILOT",
        task_id=task.task_id, attempt_id="first", codex_version="synthetic",
        lifecycle_required=True, invocation={"status":"STRUCTURED_OUTPUT_RECEIVED","returncode":0})
    return directory


def test_preview_is_scoped_and_does_not_call_models(parent, monkeypatch):
    monkeypatch.setattr(relay,"probe_claude",lambda *_: pytest.fail("no probe"))
    preview = relay.preview_relay("parent", "first", **OPTIONS)
    assert preview["focus_lines"] == [7,8,9,10]
    assert preview["recommended_agent_id"] == "claude-local"
    assert preview["research_execution_authorized"] is False
    assert "UNTRUSTED_PRIVATE_TEXT_NOT_TO_SEND" not in preview["prompt"]
    assert "UNTRUSTED_LIMITATION" not in preview["prompt"]
    assert "../private.txt" not in preview["prompt"]
    assert "split_sequences" in preview["prompt"]
    assert not has_exact_intent("PILOT", preview["child_plan_id"], relay.TASK, relay.ATTEMPT)


def test_relay_requires_explicit_consent_and_exact_preview(parent, monkeypatch):
    monkeypatch.setattr(relay,"probe_claude",lambda *_: pytest.fail("no probe"))
    with pytest.raises(ValueError,match="EXPLICIT_RELAY_MODEL_OPT_IN_REQUIRED"):
        relay.execute_relay("parent","first",claude_bin=None,approved_prompt_sha256=None,**OPTIONS)
    with pytest.raises(ValueError,match="RELAY_PROMPT_APPROVAL_MISMATCH"):
        relay.execute_relay("parent","first",claude_bin=None,approved_prompt_sha256="wrong",
                            execute=True,ack_external_model=True,**OPTIONS)


def test_parent_tampering_and_wrong_attempt_are_blocked(parent):
    with pytest.raises(ValueError,match="RELAY_PARENT_INTENT_MISSING"):
        relay.preview_relay("parent","wrong",**OPTIONS)
    (parent/"codex-final.json").write_text("{}",encoding="utf-8")
    with pytest.raises(ValueError,match="RELAY_PARENT_RECEIPT_NOT_ACCEPTED"):
        relay.preview_relay("parent","first",**OPTIONS)


def test_two_real_synthetic_children_and_one_relay_attempt(parent,monkeypatch):
    preview = relay.preview_relay("parent","first",**OPTIONS)
    monkeypatch.setattr(relay,"probe_claude",lambda *_: {
        "supported":True,"executable":sys.executable,"version":"synthetic"})
    calls=[]
    def substitute(args,prompt,seconds,lifecycle,**kw):
        calls.append(args)
        assert args[args.index("--tools")+1] == ""
        assert "--safe-mode" in args and "--strict-mcp-config" in args
        assert "--no-session-persistence" in args and "--no-chrome" in args
        assert args[args.index("--max-turns")+1] == "3"
        assert args[args.index("--max-budget-usd")+1] == "0.50"
        assert "UNTRUSTED_PRIVATE_TEXT_NOT_TO_SEND" not in prompt
        wrapper={"is_error":False,"structured_output":{
            "summary":"second independent synthetic review","observations":[],
            "limitations":["not a scientific validation"],"next_actions":[]}}
        script="import sys;sys.stdin.read();sys.stdout.write(sys.argv[1])"
        return run_tracked_child([sys.executable,"-I","-c",script,json.dumps(wrapper)],
                                 prompt,10,lifecycle,**kw)
    monkeypatch.setattr(claude,"run_tracked_child",substitute)
    kwargs=dict(claude_bin=None,approved_prompt_sha256=preview["prompt_sha256"],
                execute=True,ack_external_model=True,**OPTIONS)
    result=relay.execute_relay("parent","first",**kwargs)
    assert result["status"]=="STRUCTURED_OUTPUT_RECEIVED"
    assert result["agent_id"]=="claude-local"
    assert result["decision_type"]=="REVIEW_OUTCOME_PENDING"
    assert result["science_validated"] is False
    assert result["next_dispatch_performed"] is False
    assert result["local_evidence_check"]["process_lifecycle"]["status"]=="LIFECYCLE_DIRECT_CHILD_EXIT_RECORDED"
    assert relay.inspect_relay("parent","first")["local_byte_consistency_checked"] is True
    assert relay.execute_relay("parent","first",**kwargs)["status"]=="ALREADY_RESERVED_NO_RETRY"
    assert len(calls)==1
    report=json.loads(Path(result["private_report"]["handoff_json"]).read_text(encoding="utf-8"))
    assert report["result"]["agent_id"]=="claude-local"
    assert report["decision"]["can_auto_dispatch"] is False
    (parent/"codex-final.json").write_text("changed",encoding="utf-8")
    assert relay.inspect_relay("parent","first")["status"]=="RELAY_RECONCILIATION_REQUIRED"


def test_no_provider_does_not_reserve_second_task(parent,monkeypatch):
    preview=relay.preview_relay("parent","first",**OPTIONS)
    monkeypatch.setattr(relay,"probe_claude",lambda *_: {"supported":False})
    result=relay.execute_relay("parent","first",claude_bin=None,
        approved_prompt_sha256=preview["prompt_sha256"],execute=True,ack_external_model=True,**OPTIONS)
    assert result["status"]=="CLAUDE_NOT_CONNECTED"
    assert not has_exact_intent("PILOT",preview["child_plan_id"],relay.TASK,relay.ATTEMPT)


def test_relay_cli_preview_and_flags(parent,capsys):
    from pdrw_orchestrator.cli import main
    args=["relay","preview","--plan-id","parent","--attempt-id","first"]
    assert main(args)==0
    assert json.loads(capsys.readouterr().out)["status"]=="RELAY_PREVIEW_ONLY"
    assert main(args+["--execute"])==2
    assert "RELAY_READONLY_ACTION_REJECTS_EXECUTION_FLAGS" in capsys.readouterr().out
