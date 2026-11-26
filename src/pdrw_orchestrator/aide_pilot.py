"""Fixed public synthetic AIDE acceptance task; no model, training or launch.

The worker sees only worker/data and task.md. The review directory and this
source must not be mounted into the worker. This public reproducible fixture
is an engineering test, not a secret scientific test or a secure sandbox.
"""
from __future__ import annotations

import csv
import io
import json
import math
from pathlib import Path

from .adapters.aide import _digest, _plain, preview_aide

_PROTOCOL = "AIDE-SYNTHETIC-GROUP-RMSE-V1"
_GOAL = "Develop a CPU-only regression candidate for a synthetic sensor. Predict target from x only."
_EVAL = (
    "Read input/train.csv, input/validation.csv and input/test.csv. "
    "The fixed split is by group; fit and preprocess only on train. Use validation labels "
    "for internal search and print validation RMSE, do not merge groups or change split. "
    "Only x is a legal predictor; row_id and group_id are identifiers, not features. "
    "Use the same preprocessing on test. Save working/submission.csv with exactly row_id,prediction "
    "for every test row. Test labels are not provided. No downloads, network from generated "
    "code, GPU, manuscript or other output requirements. Independent review scores selected-code "
    "predictions, not the LLM's metric or last workspace file."
)
_PUBLIC = ("train.csv", "validation.csv", "test.csv")
_MAX_PRED_BYTES = 64 * 1024
# Equal group sizes make row RMSE equally weighted across independent groups.


def _csv(header, rows):
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    return stream.getvalue().encode("ascii")


def _rows():
    # Fixed arithmetic, not random hidden experimental data.
    rows = {}
    for group in range(12):
        for index in range(12):
            x = (((group * 17 + index * 11) % 41) - 20) / 10
            noise = (((group * 13 + index * 7) % 9) - 4) / 20
            target = round(1.5 + 2 * x + 0.35 * x * x + noise, 6)
            rows[f"g{group:02d}-{index:02d}"] = (f"g{group:02d}", x, target)
    return rows


def _fixture():
    rows = _rows()
    outputs = {}
    for name, lo, hi in (("train.csv", 0, 6), ("validation.csv", 6, 8), ("test.csv", 8, 12)):
        chosen = [(key, g, x, y) for key, (g, x, y) in rows.items()
                  if lo <= int(g[1:]) < hi]
        outputs[name] = _csv(
            ("row_id", "group_id", "x") if name == "test.csv" else ("row_id", "group_id", "x", "target"),
            (r[:3] for r in chosen) if name == "test.csv" else chosen,
        )
    return outputs


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode("ascii")


def _manifest():
    return {"protocol": _PROTOCOL, "dataset_kind": "PUBLIC_SYNTHETIC",
            "split_groups": {"train": 6, "validation": 2, "test": 4},
            "rows_per_group": 12, "legal_features": ["x"], "metric": "RMSE",
            "files": {name: {"sha256": _digest(raw), "bytes": len(raw)}
                      for name, raw in _fixture().items()}}


def _check_root(value, *, exists):
    root = Path(value)
    if not root.is_absolute() or ".." in root.parts:
        raise ValueError("PILOT_ABSOLUTE_ROOT_REQUIRED")
    for parent in reversed(tuple(root.parents)):
        _plain(parent, directory=True)
    if exists:
        _plain(root, directory=True)
    elif root.exists() or root.is_symlink():
        raise ValueError("PILOT_ROOT_ALREADY_EXISTS")
    return root


def _read(path, cap):
    _plain(path, directory=False)
    with path.open("rb") as stream:
        raw = stream.read(cap + 1)
    if not raw or len(raw) > cap:
        raise ValueError("PILOT_FILE_EMPTY_OR_OVERSIZE")
    return raw


def _write(path, raw):
    with path.open("xb") as stream:
        stream.write(raw)


def _plan(*, attempt_id, code_provider, code_model, feedback_provider, feedback_model,
          steps=3, step_timeout_seconds=60):
    return {"schema_version": "aide-dev-preview-v1", "project_id": "PUBLIC-SYNTHETIC",
            "task_id": _PROTOCOL, "attempt_id": attempt_id, "goal": _GOAL, "evaluation": _EVAL,
            "protocol_ref": _PROTOCOL, "data_manifest_sha256": _digest(_canonical(_manifest())),
            "steps": steps, "step_timeout_seconds": step_timeout_seconds, "metric_maximize": False,
            "code_provider": code_provider, "code_model": code_model,
            "feedback_provider": feedback_provider, "feedback_model": feedback_model}


def prepare(root, *, attempt_id, code_provider, code_model, feedback_provider, feedback_model,
            steps=3, step_timeout_seconds=60):
    plan = _plan(attempt_id=attempt_id, code_provider=code_provider, code_model=code_model,
                 feedback_provider=feedback_provider, feedback_model=feedback_model,
                 steps=steps, step_timeout_seconds=step_timeout_seconds)
    preview = preview_aide(plan)  # validate before creating files
    root = _check_root(root, exists=False)
    root.mkdir(exist_ok=False)
    worker, review = root / "worker", root / "review"
    (worker / "data").mkdir(parents=True)
    review.mkdir()
    for name, raw in _fixture().items():
        _write(worker / "data" / name, raw)
    _write(worker / "task.md", preview["task_file_preview"].encode("utf-8"))
    _write(review / "plan.json", _canonical(plan))
    _write(review / "manifest.json", _canonical(_manifest()))
    return verify(root)


def verify(root):
    root = _check_root(root, exists=True)
    worker, review = root / "worker", root / "review"
    for path in (worker, worker / "data", review):
        _plain(path, directory=True)
    raw_plan = _read(review / "plan.json", 32 * 1024)
    plan = json.loads(raw_plan)
    preview = preview_aide(plan)
    expected = _plan(**{key: plan[key] for key in (
        "attempt_id", "code_provider", "code_model", "feedback_provider", "feedback_model",
        "steps", "step_timeout_seconds")})
    if plan != expected or raw_plan != _canonical(expected):
        raise ValueError("PILOT_PLAN_MISMATCH")
    if _read(review / "manifest.json", 32 * 1024) != _canonical(_manifest()):
        raise ValueError("PILOT_MANIFEST_MISMATCH")
    if {p.name for p in (worker / "data").iterdir()} != set(_PUBLIC):
        raise ValueError("PILOT_DATA_FILE_SET_MISMATCH")
    for name, expected_bytes in _fixture().items():
        if _read(worker / "data" / name, 64 * 1024) != expected_bytes:
            raise ValueError("PILOT_DATA_BYTES_MISMATCH")
    if _read(worker / "task.md", 32 * 1024) != preview["task_file_preview"].encode("utf-8"):
        raise ValueError("PILOT_TASK_BYTES_MISMATCH")
    return {"status": "PUBLIC_SYNTHETIC_INPUTS_MATCHED_ONLY", "plan": plan,
            "plan_sha256": preview["plan_sha256"], "manifest": _manifest(),
            "worker_cwd_ref": "worker", "review_ref": "review",
            "argv_preview": preview["argv_preview"], "environment_preview": preview["environment_preview"],
            "required_host_checks": preview["required_host_checks"],
            "execution_authorized": False, "execute_performed": False,
            "model_calls_requested": 0, "host_isolation_verified": False,
            "scientific_validity_verified": False}


def _predictions(raw, expected):
    reader = csv.reader(io.StringIO(raw.decode("utf-8-sig"), newline=""))
    if next(reader, None) != ["row_id", "prediction"]:
        raise ValueError("PILOT_PREDICTION_HEADER_INVALID")
    result = {}
    for row in reader:
        if len(row) != 2 or row[0] not in expected or row[0] in result:
            raise ValueError("PILOT_PREDICTION_ID_INVALID")
        try:
            value = float(row[1])
        except ValueError:
            raise ValueError("PILOT_PREDICTION_VALUE_INVALID") from None
        if not math.isfinite(value) or abs(value) > 1e6:
            raise ValueError("PILOT_PREDICTION_VALUE_INVALID")
        result[row[0]] = value
    if set(result) != set(expected):
        raise ValueError("PILOT_PREDICTION_COVERAGE_INCOMPLETE")
    return result


def score(root):
    """Score only explicit review/submission.csv, never provider code or journal."""
    checked = verify(root)
    raw = _read(Path(root) / "review" / "submission.csv", _MAX_PRED_BYTES)
    return score_predictions(raw, checked["plan_sha256"])


def score_predictions(raw, plan_sha256):
    """Shared operator-side synthetic evaluator; never authenticate prediction origin."""
    rows = _rows()
    train = [(x, y) for g, x, y in rows.values() if int(g[1:]) < 6]
    test = {key: (g, x, y) for key, (g, x, y) in rows.items() if int(g[1:]) >= 8}
    prediction = _predictions(raw, test)
    # Train-only closed-form linear reference, not a provider run.
    mx = sum(x for x, _ in train) / len(train)
    my = sum(y for _, y in train) / len(train)
    slope = sum((x - mx) * (y - my) for x, y in train) / sum((x - mx)**2 for x, _ in train)

    def rmse(pred, keys):
        return math.sqrt(sum((pred(key) - test[key][2])**2 for key in keys) / len(keys))

    candidate = lambda key: prediction[key]
    baseline = lambda key: my + slope * (test[key][1] - mx)
    ids = list(test)
    groups = {}
    for group in sorted({row[0] for row in test.values()}):
        keys = [key for key in ids if test[key][0] == group]
        groups[group] = {"rows": len(keys), "candidate_rmse": rmse(candidate, keys),
                         "linear_baseline_rmse": rmse(baseline, keys)}
    cand, base = rmse(candidate, ids), rmse(baseline, ids)
    return {"status": "SYNTHETIC_PREDICTION_SCORED_ONLY",
            "plan_sha256": plan_sha256, "prediction_sha256": _digest(raw),
            "rows": len(ids), "independent_group_count": len(groups), "metric": "RMSE",
            "candidate_rmse": cand, "linear_baseline_rmse": base,
            "mean_baseline_rmse": rmse(lambda key: my, ids),
            "delta_candidate_minus_linear": cand - base, "group_scores": groups,
            "prediction_origin_verified": False, "candidate_code_binding_verified": False,
            "scientific_validity_verified": False, "execution_authorized": False,
            "model_calls_requested": 0}
