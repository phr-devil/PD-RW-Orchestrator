import csv
import json

import pytest

from pdrw_orchestrator.aide_pilot import prepare, score, verify
from pdrw_orchestrator.cli import main


def make(root):
    return prepare(root, attempt_id="pilot-1", code_provider="openai",
                   code_model="example-model", feedback_provider="anthropic",
                   feedback_model="example-feedback")


def rows(path):
    with path.open(newline="", encoding="ascii") as stream:
        return list(csv.DictReader(stream))


def predictions(root, entries):
    path = root / "review" / "submission.csv"
    with path.open("w", newline="", encoding="ascii") as stream:
        writer = csv.writer(stream)
        writer.writerow(["row_id", "prediction"])
        writer.writerows(entries)


def test_fixed_inputs_group_split_and_no_test_labels(tmp_path):
    root = tmp_path.resolve() / "pilot"
    first = make(root)
    assert first == verify(root)
    assert first["environment_preview"] == {"PYTHONUTF8": "1"}
    assert not first["execution_authorized"]
    assert first["model_calls_requested"] == 0
    splits = [rows(root / "worker" / "data" / name) for name in ("train.csv", "validation.csv", "test.csv")]
    groups = [{r["group_id"] for r in split} for split in splits]
    assert [len(g) for g in groups] == [6, 2, 4]
    assert not (groups[0] & groups[1] or groups[0] & groups[2] or groups[1] & groups[2])
    assert set(splits[2][0]) == {"row_id", "group_id", "x"}
    assert not (root / "worker" / "review").exists()
    with pytest.raises(ValueError):
        make(root)


def test_score_recomputes_and_never_certifies_origin(tmp_path):
    root = tmp_path.resolve() / "pilot"
    make(root)
    data = rows(root / "worker" / "data" / "test.csv")
    predictions(root, [(r["row_id"], 0) for r in data])
    value = score(root)
    assert value["rows"] == 48 and value["independent_group_count"] == 4
    assert value["candidate_rmse"] > value["linear_baseline_rmse"]
    assert value["linear_baseline_rmse"] < value["mean_baseline_rmse"]
    assert value["delta_candidate_minus_linear"] == pytest.approx(value["candidate_rmse"] - value["linear_baseline_rmse"])
    assert sum(x["rows"] for x in value["group_scores"].values()) == 48
    assert not value["candidate_code_binding_verified"]
    assert not value["scientific_validity_verified"]
    assert value["model_calls_requested"] == 0


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "nan", "unknown"])
def test_reject_prediction_mismatch(tmp_path, mutation):
    root = tmp_path.resolve() / "pilot"
    make(root)
    entries = [(r["row_id"], 0) for r in rows(root / "worker" / "data" / "test.csv")]
    if mutation == "missing":
        entries.pop()
    elif mutation == "duplicate":
        entries.append(entries[0])
    elif mutation == "nan":
        entries[0] = (entries[0][0], "nan")
    else:
        entries[0] = ("wrong", 0)
    predictions(root, entries)
    with pytest.raises(ValueError):
        score(root)


@pytest.mark.parametrize("target", ["worker/data/train.csv", "worker/task.md", "review/manifest.json", "review/plan.json"])
def test_reject_changed_input(tmp_path, target):
    root = tmp_path.resolve() / "pilot"
    make(root)
    path = root / target
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError):
        verify(root)


def test_reject_extra_data_file(tmp_path):
    root = tmp_path.resolve() / "pilot"
    make(root)
    (root / "worker" / "data" / "extra.csv").write_text("x", encoding="ascii")
    with pytest.raises(ValueError):
        verify(root)


def test_cli_prepare_verify_score(tmp_path, capsys):
    root = tmp_path.resolve() / "pilot"
    assert main(["aide-pilot", "prepare", "--root", str(root), "--attempt-id", "a1",
                 "--code-provider", "openai", "--code-model", "example",
                 "--feedback-provider", "openai", "--feedback-model", "example"]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "PUBLIC_SYNTHETIC_INPUTS_MATCHED_ONLY"
    assert main(["aide-pilot", "verify", "--root", str(root)]) == 0
    capsys.readouterr()
    predictions(root, [(r["row_id"], 0) for r in rows(root / "worker" / "data" / "test.csv")])
    assert main(["aide-pilot", "score", "--root", str(root)]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "SYNTHETIC_PREDICTION_SCORED_ONLY"
