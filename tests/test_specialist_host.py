import hashlib
import json
import pytest

from pdrw_orchestrator import aide_pilot, specialist_host
from pdrw_orchestrator.adapters import rdagent, aide_install
from pdrw_orchestrator.cli import main
from pdrw_orchestrator.policy import Guidance


def source(root, monkeypatch, provider):
    root.mkdir()
    raw = b"source\n"
    relative = {"aide": "aide/run.py", "rdagent": "rdagent/app/cli.py", "arc": "researchclaw/cli.py"}[provider]
    if provider == "aide":
        monkeypatch.setattr(aide_install, "_BLOBS", {relative: aide_install._git_blob(raw)})
    else:
        monkeypatch.setitem(aide_install._OTHER_BLOBS, provider, {relative: aide_install._git_blob(raw)})
    path = root / relative
    path.parent.mkdir(parents=True)
    path.write_bytes(raw)
    return path


def aide(root):
    aide_pilot.prepare(root, attempt_id="a1", code_provider="openai", code_model="example",
                       feedback_provider="openai", feedback_model="example")


def arc_plan(raw):
    return {"schema_version": "arc-discovery-preview-v1", "project_id": "P", "task_id": "T",
            "attempt_id": "a1", "public_topic": "Public research topic",
            "research_scope": "Literature only", "max_papers": 10,
            "config_sha256": hashlib.sha256(raw).hexdigest()}


def test_host_aide_prepare_and_intake(tmp_path, monkeypatch, capsys):
    root = tmp_path.resolve() / "pilot"
    aide(root)
    checkout = tmp_path.resolve() / "source"
    path = source(checkout, monkeypatch, "aide")
    value = specialist_host.prepare("aide", root, source_root=checkout)
    assert value["status"] == "HOST_REVIEW_REQUIRED"
    assert value["argv"][0] == "aide" and not value["execution_authorized"]
    assert not value["execute_performed"]
    assert value["local_cwd"] == str(root / "worker")
    path.write_bytes(b"tampered")
    assert "PINNED_SELECTED_SOURCE_NOT_MATCHED" in specialist_host.prepare("aide", root, source_root=checkout)["blockers"]
    run = root / "worker" / "logs" / "0-a1"
    run.mkdir(parents=True)
    (run / "best_solution.py").write_text("raise RuntimeError('never execute')", encoding="utf-8")
    (run / "journal.json").write_text("{}", encoding="utf-8")
    assert "WORKER_NOT_FRESH_RECONCILE" in specialist_host.prepare("aide", root)["blockers"]
    packet = specialist_host.collect("aide", root, run_name="0-a1")
    assert packet["agent_result"]["deliverables"]["code_refs"] == ["worker/logs/0-a1/best_solution.py"]
    assert not packet["artifact_observation"]["plan_binding_verified"]
    path = tmp_path / "intake.json"
    path.write_text(json.dumps(packet), encoding="utf-8")
    assert main(["advise", "--intake-file", str(path)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["decision"]["decision_type"] == "INDEPENDENT_REVIEW"
    assert not result["scientific_completion_verified"]
    assert main(["advise", "--intake-file", str(path), "--task-file", "other"]) == 2
    capsys.readouterr()
    packet["agent_result"]["task_id"] = "wrong"
    path.write_text(json.dumps(packet), encoding="utf-8")
    assert main(["advise", "--intake-file", str(path)]) == 2


def test_rd_config_checked_not_exposed(tmp_path, monkeypatch):
    root = tmp_path.resolve() / "rd"
    raw = b"PRIVATE_CONFIG_EXAMPLE=not-a-real-secret\n"
    rdagent.prepare(root, attempt_id="rd1", config_sha256=hashlib.sha256(raw).hexdigest())
    checkout = tmp_path.resolve() / "source"
    source(checkout, monkeypatch, "rdagent")
    value = specialist_host.prepare("rdagent", root, source_root=checkout)
    assert value["status"] == "HOST_PREPARATION_BLOCKED"
    (root / "worker" / ".env").write_bytes(raw)
    value = specialist_host.prepare("rdagent", root, source_root=checkout)
    assert value["status"] == "HOST_REVIEW_REQUIRED"
    assert value["config_observation"] == "DECLARED_BYTES_MATCH"
    assert "not-a-real-secret" not in json.dumps(value)
    assert not value["effective_config_verified"]
    export = root / "review" / "candidate"
    export.mkdir()
    for name in ("main.py", "scores.csv", "submission.csv"):
        (export / name).write_text("fixture", encoding="utf-8")
    packet = specialist_host.collect("rdagent", root)
    assert packet["agent_result"]["deliverables"]["code_refs"] == ["review/candidate/main.py"]
    assert not packet["execution_authorized"]


def test_arc_config_and_policy(tmp_path, monkeypatch):
    root = tmp_path.resolve() / "arc"
    root.mkdir()
    raw = b"synthetic fixture, not an actual usable config\n"
    plan = arc_plan(raw)
    checkout = tmp_path.resolve() / "source"
    source(checkout, monkeypatch, "arc")
    (root / "config.arc.yaml").write_bytes(raw)
    value = specialist_host.prepare("arc", root, source_root=checkout, plan=plan)
    assert value["status"] == "HOST_REVIEW_REQUIRED"
    assert value["argv"][value["argv"].index("--to-stage")+1] == "LITERATURE_COLLECT"
    assert not value["effective_config_verified"]
    deny = Guidance.from_dict({"id": "DENY", "level": "requirement", "source": "local",
        "task_types": ["*"], "text": "No network", "deny_effects": ["network"]})
    value = specialist_host.prepare("arc", root, source_root=checkout, plan=plan, rules=(deny,))
    assert "LOCAL_POLICY_EFFECT_DENIED" in value["blockers"]
    (root / "config.arc.yaml").write_bytes(b"changed")
    assert "PROVIDER_CONFIG_NOT_MATCHED" in specialist_host.prepare("arc", root, source_root=checkout, plan=plan)["blockers"]


def test_arc_intake_rebases_and_preserves_review(tmp_path):
    from pdrw_orchestrator.adapters.arc import _FILES
    root = tmp_path.resolve()
    run = root / "run"
    for ref in _FILES:
        path = run / ref
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture", encoding="utf-8")
    (run / "pipeline_summary.json").write_text(json.dumps({
        "from_stage": 1, "final_stage": 4, "stages_executed": 4, "stages_done": 4,
        "stages_failed": 0, "stages_blocked": 0, "stages_paused": 0,
        "final_status": "done", "degraded": False}), encoding="utf-8")
    (run / "stage-04/candidates.jsonl").write_text('{"is_placeholder":true}\n', encoding="utf-8")
    (run / "stage-04/search_meta.json").write_text('{"total_candidates":1}', encoding="utf-8")
    packet = specialist_host.collect("arc", root, plan=arc_plan(b"fixture"))
    task, raw = specialist_host.unpack_intake(packet)
    assert task.task_type == "discovery"
    assert all(x.startswith("run/") for x in raw["deliverables"]["report_refs"])
    assert raw["execution"]["status"] == "NEEDS_REVIEW"
    assert not raw["scientific_completion_verified"]
