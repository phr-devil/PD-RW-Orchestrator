import hashlib
import json

import pytest

from pdrw_orchestrator import specialist_plan, specialist_host
from pdrw_orchestrator.adapters import tooluniverse
from pdrw_orchestrator.cli import main
from pdrw_orchestrator.models import TaskPacket
from pdrw_orchestrator.policy import Guidance


def lookup_task():
    return TaskPacket(task_id="L1", project_id="P", task_type="discovery",
                      capability="literature_lookup", objective="Private local context, not provider-facing.",
                      budget={"max_model_calls": 0})


def lookup_options():
    return {"attempt_id":"a1", "operation":"search", "public_text":"public wearable sensor", "limit":2}


def arc_options():
    return {"attempt_id":"a2", "public_topic":"public wearable sensor", "research_scope":"Literature only",
            "max_papers":10, "config_sha256":"a"*64}


def dev_options():
    return {"attempt_id":"a3", "goal":"Scoped regression", "evaluation":"Fixed group DEV",
            "protocol_ref":"P/PROTO", "data_manifest_sha256":"b"*64,
            "steps":3, "step_timeout_seconds":60, "metric_maximize":False,
            "code_provider":"openai", "code_model":"example",
            "feedback_provider":"openai", "feedback_model":"example"}


def lookup_intake(root, monkeypatch):
    plan = specialist_plan.compile_plan(lookup_task(), "public_topic", lookup_options())["native_plan"]
    monkeypatch.setattr(tooluniverse, "_native_call", lambda *args: {
        "status":"success", "count":1, "data":[{"DOI":"10.1234/example","title":["Example"]}]})
    packet = tooluniverse.query(plan, root, "unused", execute=True, ack_public_network=True)
    return packet


def test_compile_uses_explicit_native_text_and_no_permissions(tmp_path, capsys):
    task = lookup_task()
    value = specialist_plan.compile_plan(task, "public_topic", lookup_options())
    assert value["native_plan"]["public_text"] == "public wearable sensor"
    assert "Private local context" not in json.dumps(value["native_plan"])
    assert value["native_plan_sha256"] == tooluniverse.preview(value["native_plan"])["plan_sha256"]
    assert not value["execution_authorized"]
    path = tmp_path.resolve() / "plan.json"
    specialist_plan.export_plan(value, path)
    assert json.loads(path.read_text()) == value["native_plan"]
    with pytest.raises(ValueError):
        specialist_plan.export_plan(value, path)
    task_file, opt_file = tmp_path / "task.json", tmp_path / "options.json"
    task_file.write_text(json.dumps(task.to_dict()), encoding="utf-8")
    opt_file.write_text(json.dumps(lookup_options()), encoding="utf-8")
    assert main(["specialists","compile","--scope","public_topic","--task-file",str(task_file),
                 "--options-file",str(opt_file),"--out-plan",str(tmp_path.resolve()/"other.json")]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "NATIVE_PLAN_COMPILED_REVIEW_REQUIRED"


def test_cross_provider_relay_checks_prior_bytes_and_review_ref(tmp_path, monkeypatch, capsys):
    root = tmp_path.resolve() / "lookup"
    packet = lookup_intake(root, monkeypatch)
    task = TaskPacket(task_id="L2", project_id="P", task_type="discovery", objective="Broaden search",
                      evidence_refs=("P/REVIEW-L1",))
    value = specialist_plan.compile_plan(task, "public_topic", arc_options(),
             prior=packet, prior_root=root, review_ref="P/REVIEW-L1")
    assert value["route"]["recommended_candidate"] == "arc"
    assert value["previous"]["provider"] == "tooluniverse"
    assert value["previous"]["artifact_observation"]["artifact_bytes_reverified"]
    assert not value["previous"]["review_contents_verified"]
    assert not value["scientific_transition_verified"]
    assert "P/REVIEW-L1" not in json.dumps(value["native_plan"])
    dev = TaskPacket(task_id="D1", project_id="P", task_type="code_experiment", objective="Evaluate",
                     protocol_refs=("P/PROTO",), evidence_refs=("P/REVIEW-L1",))
    result = specialist_plan.compile_plan(dev, "staged_dev", dev_options(),
               prior=packet, prior_root=root, review_ref="P/REVIEW-L1")
    assert result["native_plan"]["protocol_ref"] == "P/PROTO"
    assert result["route"]["recommended_candidate"] == "aide"
    assert not result["previous"]["original_authorization_inherited"]
    path = tmp_path / "intake.json"
    path.write_text(json.dumps(packet), encoding="utf-8")
    assert main(["advise","--intake-file",str(path),"--intake-root",str(root)]) == 0
    advice = json.loads(capsys.readouterr().out)
    assert advice["specialist_intake"]["artifact_bytes_reverified_by_advise"]
    assert advice["decision"]["decision_type"] == "INDEPENDENT_REVIEW"
    with pytest.raises(ValueError, match="REVIEW_REF"):
        specialist_plan.compile_plan(dev,"staged_dev",dev_options(),
             prior=packet,prior_root=root,review_ref="wrong")
    with pytest.raises(ValueError, match="IDENTITY"):
        specialist_plan.compile_plan(lookup_task(),"public_topic",lookup_options(),
             prior=packet,prior_root=root,review_ref="P/REVIEW-L1")
    original = (root / "literature.json").read_bytes()
    (root / "literature.json").write_bytes(b"X"+original[1:])
    with pytest.raises(ValueError, match="BYTES_MISMATCH"):
        specialist_plan.compile_plan(dev,"staged_dev",dev_options(),
             prior=packet,prior_root=root,review_ref="P/REVIEW-L1")


def test_scope_policy_and_protocol():
    dev = TaskPacket(task_id="D1",project_id="P",task_type="code_experiment",objective="Evaluate",
                     protocol_refs=("P/PROTO",))
    with pytest.raises(ValueError,match="PROTOCOL"):
        specialist_plan.compile_plan(dev,"staged_dev",dict(dev_options(),protocol_ref="other"))
    with pytest.raises(ValueError,match="OPTIONS"):
        specialist_plan.compile_plan(dev,"staged_dev",dict(dev_options(),authorization=True))
    assert specialist_plan.compile_plan(dev,"original_local",{})["native_plan"] is None
    assert specialist_plan.compile_plan(dev,"public_synthetic",{})["status"] == "FIXED_PILOT_PREPARATION_REQUIRED"
    deny = Guidance.from_dict({"id":"N","level":"requirement","source":"user","task_types":["*"],
                               "text":"deny network","deny_effects":["network"]})
    value = specialist_plan.compile_plan(lookup_task(),"public_topic",lookup_options(),rules=(deny,))
    assert value["native_plan"] is None
    assert not value["execution_authorized"]
