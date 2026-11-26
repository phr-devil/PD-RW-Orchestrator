import hashlib
import json

import pytest

from pdrw_orchestrator import aide_dev, specialist_host
from pdrw_orchestrator.models import TaskPacket
from pdrw_orchestrator.specialists import recommend
from pdrw_orchestrator.policy import Guidance
from pdrw_orchestrator.cli import main


def fixture(root):
    data = root / "worker" / "data"
    data.mkdir(parents=True)
    review = root / "review"
    review.mkdir()
    raw = b"x,y\n1,2\n3,4\n"
    (data / "train.csv").write_bytes(raw)
    manifest = {"schema_version": "aide-dev-snapshot-v1", "project_id": "P", "task_id": "T",
                "scope": "DEV_ONLY_DECLARED", "files": [{"name": "train.csv",
                    "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}]}
    manifest_bytes = json.dumps(manifest).encode()
    (review / "manifest.json").write_bytes(manifest_bytes)
    return {"schema_version": "aide-dev-preview-v1", "project_id": "P", "task_id": "T",
            "attempt_id": "a1", "goal": "Candidate regression", "evaluation": "Fixed group DEV",
            "protocol_ref": "P/PROTOCOL", "data_manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
            "steps": 3, "step_timeout_seconds": 60, "metric_maximize": False,
            "code_provider": "openai", "code_model": "example", "feedback_provider": "openai",
            "feedback_model": "example"}


def test_dev_task_stage_and_collect(tmp_path):
    root = tmp_path.resolve() / "dev"
    plan = fixture(root)
    value = aide_dev.stage(root, plan)
    assert value["snapshot_file_count"] == 1 and not value["actual_data_scope_verified"]
    assert not value["execution_authorized"]
    with pytest.raises(ValueError):
        aide_dev.stage(root, plan)
    handoff = specialist_host.prepare("aide", root, plan=plan)
    assert handoff["task"]["project_id"] == "P"
    assert handoff["task"]["protocol_refs"] == ("P/PROTOCOL",)
    assert "SELECTED_SOURCE_NOT_CHECKED" in handoff["blockers"]
    run = root / "worker" / "logs" / "0-a1"
    run.mkdir(parents=True)
    (run / "best_solution.py").write_text("pass", encoding="utf-8")
    (run / "journal.json").write_text("{}", encoding="utf-8")
    intake = specialist_host.collect("aide", root, plan=plan, run_name="0-a1")
    assert intake["task"]["project_id"] == "P"
    assert not intake["execution_authorized"]
    with pytest.raises(ValueError):
        specialist_host.collect("aide", root, plan=plan, run_name="0-a1", score_replay=True)


def test_snapshot_mutation(tmp_path):
    root = tmp_path.resolve() / "dev"
    plan = fixture(root)
    aide_dev.stage(root, plan)
    path = root / "worker" / "data" / "train.csv"
    path.write_bytes(b"x,y\n9,2\n3,4\n")
    with pytest.raises(ValueError, match="BYTES_MISMATCH"):
        aide_dev.verify(root, plan)


def test_no_unknown_extra_data(tmp_path):
    root = tmp_path.resolve() / "dev"
    plan = fixture(root)
    (root / "worker" / "data" / "extra.csv").write_text("x", encoding="ascii")
    with pytest.raises(ValueError):
        aide_dev.stage(root, plan)
    assert not (root / "worker" / "task.md").exists()


def test_recommend_task_scope_budget_and_deny():
    task = TaskPacket(task_id="T", project_id="P", task_type="code_experiment", objective="Regression")
    result = recommend(task, scope="staged_dev")
    assert result["recommended_candidate"] == "aide"
    assert not result["execution_authorized"]
    assert recommend(task, scope="original_local")["recommended_candidate"] is None
    assert recommend(task, scope="public_synthetic")["alternatives"] == ["rdagent"]
    denied = Guidance.from_dict({"id": "N", "source": "user", "level": "requirement",
         "task_types": ["*"], "text": "no network", "deny_effects": ["network"]})
    assert recommend(task, scope="staged_dev", rules=(denied,))["recommended_candidate"] is None
    zero = TaskPacket(task_id="T", project_id="P", task_type="code_experiment", objective="Regression",
                      budget={"max_model_calls": 0})
    assert recommend(zero, scope="staged_dev")["recommended_candidate"] is None


def test_recommend_cli(tmp_path, capsys):
    path = tmp_path / "task.json"
    path.write_text(json.dumps({"task_id":"T","project_id":"P","task_type":"discovery",
                                "objective":"Public question"}), encoding="utf-8")
    assert main(["specialists", "recommend", "--task-file", str(path), "--scope", "public_topic"]) == 0
    assert json.loads(capsys.readouterr().out)["recommended_candidate"] == "arc"
