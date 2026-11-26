"""Pinned RD-Agent custom DataScienceScen pilot, no dispatch.

Reuses the existing public grouped fixture and independent evaluator. Native
TestEval injects answer files into the generated-code workspace; do not create
its eval dataset. Only operator-selected candidate exports are inspected.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .. import aide_pilot as fixture
from ..aide_dev import check_manifest_files
from ..specialists import candidates
from .aide import _digest, _plain

_COMP = "pdrw-synthetic-sensor"
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}\Z")
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_DESCRIPTION = """# Public synthetic sensor regression
Predict target from x only. Fixed grouped split:
workspace_input/train.csv (72 labeled rows, six groups),
workspace_input/validation.csv (24 labeled rows, two different groups),
workspace_input/test.csv (48 unlabeled rows, four different groups).
Fit and preprocess only on train. Select using validation RMSE (lower is
better). Do not merge splits or use row_id/group_id as predictors. Keep
the fixed group assignments. Output main.py and any required local modules,
scores.csv with model index including ensemble and a single RMSE column
computed on validation, and submission.csv with exactly row_id,prediction
for every test row. Use the IDs from test.csv, not sample_submission.csv.
No test answers, test score feedback, downloads, GPU, generated-code network,
writing or external data. No evaluator changes. Candidate scores are advisory;
an independent operator will replay selected code and score its predictions.
"""
_MAX = 4 * 1024 * 1024


def _plan(attempt_id, loops, steps, timeout_seconds, config_sha256):
    if not isinstance(attempt_id, str) or not _ID.fullmatch(attempt_id):
        raise ValueError("RDAGENT_ATTEMPT_ID_INVALID")
    if (type(loops) is not int or not 1 <= loops <= 2 or type(steps) is not int
            or not 1 <= steps <= 10 or type(timeout_seconds) is not int
            or not 60 <= timeout_seconds <= 1800):
        raise ValueError("RDAGENT_PILOT_BUDGET_INVALID")
    if not isinstance(config_sha256, str) or not _SHA.fullmatch(config_sha256):
        raise ValueError("RDAGENT_CONFIG_DIGEST_INVALID")
    return {"schema_version": "rdagent-synthetic-pilot-v1", "project_id": "PUBLIC-SYNTHETIC",
            "task_id": "RDAGENT-SYNTHETIC-GROUP-RMSE-V1", "attempt_id": attempt_id,
            "competition": _COMP, "loops": loops, "steps": steps,
            "timeout_seconds": timeout_seconds, "provider_config_sha256_declared": config_sha256,
            "data_manifest_sha256": _digest(fixture._canonical(fixture._manifest()))}


def _native_files():
    files = dict(fixture._fixture())
    # Format only: do not expose any actual test answers.
    files["sample_submission.csv"] = fixture._csv(("row_id", "prediction"),
        ((key, 0) for key, (g, _, _) in fixture._rows().items() if int(g[1:]) >= 8))
    files["description.md"] = _DESCRIPTION.encode("ascii")
    return files


def _expected_files():
    return {f"{prefix}/{name}": raw
            for prefix in (_COMP, "sample/" + _COMP)
            for name, raw in _native_files().items()}


def prepare(root, *, attempt_id, loops=1, steps=5, timeout_seconds=600, config_sha256):
    plan = _plan(attempt_id, loops, steps, timeout_seconds, config_sha256)
    root = fixture._check_root(root, exists=False)
    root.mkdir(exist_ok=False)
    data = root / "worker" / "ds_data"
    review = root / "review"
    data.mkdir(parents=True)
    review.mkdir()
    for ref, raw in _expected_files().items():
        path = data / ref
        path.parent.mkdir(parents=True, exist_ok=True)
        fixture._write(path, raw)
    fixture._write(review / "plan.json", fixture._canonical(plan))
    return verify(root)


def _verify_tree(data, expected):
    # Exact tree: no eval/standard-answer dataset, no unexpected files,
    # no links/reparse points. Bounded traversal of known directories only.
    dirs = {str(Path(ref).parent).replace("\\", "/") for ref in expected}
    dirs.add("sample")
    for rel in [".", *sorted(dirs)]:
        folder = data / rel
        _plain(folder, directory=True)
        prefix = "" if rel == "." else rel + "/"
        children = {ref[len(prefix):].split("/")[0] for ref in [*expected, *dirs]
                    if ref.startswith(prefix) and ref != rel}
        if {p.name for p in folder.iterdir()} != children:
            raise ValueError("RDAGENT_DATA_TREE_MISMATCH")
    for ref, raw in expected.items():
        if fixture._read(data / ref, 64 * 1024) != raw:
            raise ValueError("RDAGENT_DATA_BYTES_MISMATCH")


def verify(root):
    root = fixture._check_root(root, exists=True)
    worker, review = root / "worker", root / "review"
    for path in (worker, review):
        _plain(path, directory=True)
    raw = fixture._read(review / "plan.json", 32 * 1024)
    plan = json.loads(raw)
    if not isinstance(plan, dict):
        raise ValueError("RDAGENT_PLAN_INVALID")
    expected = _plan(plan["attempt_id"], plan["loops"], plan["steps"], plan["timeout_seconds"],
                     plan["provider_config_sha256_declared"])
    if plan != expected or raw != fixture._canonical(expected):
        raise ValueError("RDAGENT_PLAN_MISMATCH")
    _verify_tree(worker / "ds_data", _expected_files())
    return _native_preview(root, plan, _digest(raw), "RDAGENT_PUBLIC_SYNTHETIC_INPUTS_MATCHED_ONLY")


def _native_preview(root, plan, digest, status):
    worker = root / "worker"
    revision = next(row["revision"] for row in candidates()["candidates"] if row["id"] == "rdagent")
    return {"status": status, "plan": plan,
            "plan_sha256": digest, "upstream_revision": revision,
            "worker_cwd_ref": "worker", "review_ref": "review",
            "argv_preview": ["rdagent", "data_science", "--competition", plan["competition"],
                             "--no-checkout", "--loop-n", str(plan["loops"]),
                             "--step-n", str(plan["steps"]), "--timeout", str(plan["timeout_seconds"]) + "s"],
            "environment_preview": {
                "DS_SCEN": "rdagent.scenarios.data_science.scen.DataScienceScen",
                "DS_LOCAL_DATA_PATH": str(worker / "ds_data"),
                "PYTHONUTF8": "1", "DS_EVAL_SUB_DIR": "eval",
                "DS_SAMPLE_DATA_BY_LLM": "False", "DS_CODER_ON_WHOLE_PIPELINE": "True",
                "DS_IF_USING_MLE_DATA": "False", "DS_ENABLE_LOG_ARCHIVE": "False",
                "DS_ENABLE_KNOWLEDGE_BASE": "False", "DS_ENABLE_RESEARCH_RAG": "False",
                "DS_ENABLE_MCP_DOCUMENTATION_SEARCH": "False", "DS_ALLOW_LONGER_TIMEOUT": "False",
                "DS_DEBUG_TIMEOUT": "120", "DS_FULL_TIMEOUT": "120",
                "DS_CODER_MAX_LOOP": "2", "DS_RUNNER_MAX_LOOP": "1", "DS_MAX_TRACE_NUM": "1"},
            "required_host_checks": [
                "Pinned isolated RD-Agent runtime and existing approved Docker/Conda environment; no automatic image pulls.",
                "Verify actual model configuration digest and provider/model/budget; use separate approved credentials.",
                "Map DS_LOCAL_DATA_PATH to actual host-visible worker directory; never mount review or source truth generator. Native scenario describes data to the model: inspect actual egress, not only generated-code network.",
                "No test_eval answers, Kaggle/MLE-Bench, arbitrary resume, unapproved network or generated-code credentials.",
                "Inspect effective environment overrides and containment; native timeout/loop caps are not total hard limits.",
                "Review selected workspace and replay exact code independently before exporting predictions."],
            "native_test_eval_enabled_intent": False, "effective_native_config_verified": False,
            "provider_config_binding_verified": False, "hard_total_budget_enforced": False,
            "host_isolation_verified": False, "execution_authorized": False,
            "execute_performed": False, "model_calls_requested": 0,
            "scientific_validity_verified": False}


def collect(root, plan=None):
    checked = verify(root) if plan is None else verify_dev(root, plan)
    export = Path(root) / "review" / "candidate"
    _plain(export, directory=True)
    # Deliberately do not inspect serialized sessions or auto-select SOTA.
    artifacts = []
    for name in ("main.py", "scores.csv", "submission.csv"):
        raw = fixture._read(export / name, _MAX)
        artifacts.append({"ref": "review/candidate/" + name, "sha256": _digest(raw), "bytes": len(raw)})
    plan = checked["plan"]
    return {"status": "RDAGENT_SELECTED_EXPORT_BYTES_OBSERVED_ONLY", "artifacts": artifacts,
            "plan_sha256_declared": checked["plan_sha256"], "complete_code_bundle_verified": False,
            "process_completion_verified": False, "plan_binding_verified": False,
            "scientific_validity_verified": False, "execution_authorized": False, "model_calls_requested": 0,
            "agent_result": {"schema_version": "2.0", "project_id": plan["project_id"],
                "task_id": plan["task_id"], "agent_id": "rdagent", "attempt_id": plan["attempt_id"],
                "execution": {"status": "NEEDS_REVIEW", "budget_exhausted": False},
                "deliverables": {"code_refs": [artifacts[0]["ref"]], "run_refs": [],
                    "evidence_refs": [artifacts[1]["ref"], artifacts[2]["ref"]], "report_refs": []},
                "findings": [], "scientific_assessment": {"claim_status": "NOT_ASSESSED",
                    "protocol_status": "NOT_ASSESSED", "outcome": "NOT_ASSESSED", "review_required": True},
                "unresolved_issues": ["Operator-selected export only; native scores and prediction origin unverified.",
                    "main.py may depend on other files; preserve and independently audit complete selected workspace.",
                    "Artifact references are relative to attempt root, not original PD-RW Runs."],
                "next_action_candidates": ["Replay selected full code bundle in a fresh isolated workspace; independently score predictions."],
                "authorization_verified": False, "scientific_completion_verified": False}}


def score(root):
    checked = verify(root)
    raw = fixture._read(Path(root) / "review" / "submission.csv", fixture._MAX_PRED_BYTES)
    result = fixture.score_predictions(raw, checked["plan_sha256"])
    result["provider"] = "rdagent"
    return result


_DEV_FIELDS = {"schema_version", "project_id", "task_id", "attempt_id", "goal",
               "evaluation", "protocol_ref", "data_manifest_sha256", "loops", "steps",
               "timeout_seconds", "provider_config_sha256_declared"}
_DEV_COMP = "pdrw-dev-task"


def preview_dev(plan):
    if (not isinstance(plan, dict) or set(plan) != _DEV_FIELDS
            or plan["schema_version"] != "rdagent-dev-preview-v1"):
        raise ValueError("RDAGENT_DEV_PLAN_INVALID")
    for key in ("project_id", "task_id", "attempt_id"):
        if not isinstance(plan[key], str) or not _ID.fullmatch(plan[key]):
            raise ValueError("RDAGENT_DEV_ID_INVALID")
    if plan["project_id"] == "PUBLIC-SYNTHETIC":
        raise ValueError("USE_FIXED_PILOT_FOR_SYNTHETIC_ID")
    _plan(plan["attempt_id"], plan["loops"], plan["steps"], plan["timeout_seconds"],
          plan["provider_config_sha256_declared"])
    for key in ("goal", "evaluation", "protocol_ref"):
        if not isinstance(plan[key], str) or not plan[key].strip() or len(plan[key]) > 3000 or "\x00" in plan[key]:
            raise ValueError("RDAGENT_DEV_TEXT_INVALID")
    if not isinstance(plan["data_manifest_sha256"], str) or not _SHA.fullmatch(plan["data_manifest_sha256"]):
        raise ValueError("RDAGENT_DEV_MANIFEST_INVALID")
    description = (
        "# Scoped DEV research task\nGoal: " + plan["goal"] + "\nEvaluation: " + plan["evaluation"] +
        "\nUse only the provided DEV data under workspace_input. Preserve the independent units, "
        "legal features, splits and matched baselines defined by the approved original protocol. "
        "Use validation feedback only. Do not modify evaluation, access reserved data, download data, "
        "use unapproved external tools or write a paper. Output main.py and required local modules, "
        "scores.csv (validation metric, including ensemble) and submission.csv under the specified format. "
        "Native scores and generated code require independent review and replay.\n")
    return {"status": "RDAGENT_DEV_PREVIEW_ONLY", "plan_sha256": _digest(fixture._canonical(plan)),
            "description": description, "execution_authorized": False, "model_calls_requested": 0}


def _dev_snapshot(root, plan, *, staged):
    preview = preview_dev(plan)
    root = fixture._check_root(root, exists=True)
    worker, review = root / "worker", root / "review"
    data = worker / "ds_data"
    for path in (worker, review, data):
        _plain(path, directory=True)
    if {p.name for p in data.iterdir()} != {_DEV_COMP, "sample"}:
        raise ValueError("RDAGENT_DEV_DATA_TREE_MISMATCH")
    sample = data / "sample"
    _plain(sample, directory=True)
    if {p.name for p in sample.iterdir()} != {_DEV_COMP}:
        raise ValueError("RDAGENT_DEV_SAMPLE_TREE_MISMATCH")
    folders = (data / _DEV_COMP, sample / _DEV_COMP)
    counts = []
    for folder in folders:
        counts.append(check_manifest_files(review, folder, plan,
                      extra_names=("description.md",) if staged else ()))
        if staged and fixture._read(folder / "description.md", 32 * 1024) != preview["description"].encode("utf-8"):
            raise ValueError("RDAGENT_DEV_DESCRIPTION_BYTES_MISMATCH")
    # Both data trees are identical, operator-staged, and contain only
    # manifest files. The optional native eval tree must never be mounted.
    return root, preview, counts[0], folders


def stage_dev(root, plan):
    root, preview, _, folders = _dev_snapshot(root, plan, staged=False)
    if {p.name for p in (root / "worker").iterdir()} - {"ds_data", ".env"}:
        raise ValueError("RDAGENT_DEV_WORKER_NOT_FRESH")
    for folder in folders:
        fixture._write(folder / "description.md", preview["description"].encode("utf-8"))
    return verify_dev(root, plan)


def verify_dev(root, plan):
    root, preview, (count, total), _ = _dev_snapshot(root, plan, staged=True)
    native = _native_preview(root, {**plan, "competition": _DEV_COMP}, preview["plan_sha256"],
                             "RDAGENT_DECLARED_DEV_SNAPSHOT_BYTES_MATCH_ONLY")
    native["plan"] = plan
    native.update({"snapshot_file_count": count, "snapshot_bytes_per_tree": total,
                   "actual_data_scope_verified": False, "original_grant_verified": False,
                   "external_transfer_authorized": False})
    native["required_host_checks"].append("Operator must approve actual DEV bytes and data descriptions sent to model; provide a project-specific independent evaluator. Never use the synthetic scorer for this task.")
    return native
