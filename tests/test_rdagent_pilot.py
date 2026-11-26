import csv
import json

import pytest

from pdrw_orchestrator.adapters import rdagent
from pdrw_orchestrator import aide_pilot
from pdrw_orchestrator.agent_result import normalize_result
from pdrw_orchestrator.models import TaskPacket
from pdrw_orchestrator.cli import main


def prepare(root, **changes):
    kwargs = {"attempt_id": "rd-1", "config_sha256": "a"*64}
    kwargs.update(changes)
    return rdagent.prepare(root, **kwargs)


def test_native_layout_and_constraints(tmp_path):
    root = tmp_path.resolve() / "rd"
    value = prepare(root)
    assert value == rdagent.verify(root)
    assert not value["execution_authorized"]
    assert not value["effective_native_config_verified"]
    data = root / "worker" / "ds_data"
    assert not (data / "eval").exists()
    for ref, raw in aide_pilot._fixture().items():
        assert (data / rdagent._COMP / ref).read_bytes() == raw
        assert (data / "sample" / rdagent._COMP / ref).read_bytes() == raw
    assert value["environment_preview"]["DS_SAMPLE_DATA_BY_LLM"] == "False"
    assert value["environment_preview"]["DS_IF_USING_MLE_DATA"] == "False"
    assert "--no-checkout" in value["argv_preview"]
    assert "--loop-n" in value["argv_preview"]
    with pytest.raises(ValueError):
        prepare(root)


@pytest.mark.parametrize("changes", [{"loops": 3}, {"steps": True}, {"timeout_seconds": 0},
    {"attempt_id": "../bad"}, {"config_sha256": "invalid"}])
def test_invalid_plan_no_write(tmp_path, changes):
    root = tmp_path.resolve() / "rd"
    with pytest.raises(ValueError):
        prepare(root, **changes)
    assert not root.exists()


@pytest.mark.parametrize("change", ["eval", "extra", "tamper"])
def test_reject_tampered_inputs(tmp_path, change):
    root = tmp_path.resolve() / "rd"
    prepare(root)
    data = root / "worker" / "ds_data"
    if change == "eval":
        (data / "eval").mkdir()
    elif change == "extra":
        (data / rdagent._COMP / "answers.csv").write_text("x", encoding="ascii")
    else:
        (data / "sample" / rdagent._COMP / "train.csv").write_text("changed", encoding="ascii")
    with pytest.raises(ValueError):
        rdagent.verify(root)


def test_collect_and_shared_score(tmp_path):
    root = tmp_path.resolve() / "rd"
    prepare(root)
    export = root / "review" / "candidate"
    export.mkdir()
    for name in ("main.py", "scores.csv", "submission.csv"):
        (export / name).write_text("untrusted", encoding="ascii")
    result = rdagent.collect(root)
    assert not result["complete_code_bundle_verified"]
    raw = result["agent_result"]
    norm = normalize_result(raw, TaskPacket(task_id=raw["task_id"], project_id=raw["project_id"],
                                            task_type="analysis", objective="Review"))
    assert norm["execution"]["reported_status"] == "NEEDS_REVIEW"
    assert not norm["scientific_completion_verified"]
    test = {key: row for key, row in aide_pilot._rows().items() if int(row[0][1:]) >= 8}
    pred = aide_pilot._csv(("row_id", "prediction"), ((key, 0) for key in test))
    (root / "review" / "submission.csv").write_bytes(pred)
    score = rdagent.score(root)
    common = aide_pilot.score_predictions(pred, score["plan_sha256"])
    assert score == dict(common, provider="rdagent")
    assert not score["prediction_origin_verified"]


def test_cli(tmp_path, capsys):
    root = tmp_path.resolve() / "rd"
    assert main(["rdagent-pilot", "prepare", "--root", str(root), "--attempt-id", "r1",
                 "--config-sha256", "a"*64]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "RDAGENT_PUBLIC_SYNTHETIC_INPUTS_MATCHED_ONLY"
    assert main(["rdagent-pilot", "verify", "--root", str(root)]) == 0
    assert json.loads(capsys.readouterr().out)["model_calls_requested"] == 0
