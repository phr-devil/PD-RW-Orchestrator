"""AIDE native interface translation and local artifact intake; never launches code.

Pinned upstream CLI uses OmegaConf overrides and a numeric prefix for exp_name.
The operator must materialize the reviewed task file and DEV-only snapshot in a
fresh isolated attempt. No caller-supplied flag or hash establishes permission.
"""
from __future__ import annotations

import hashlib
import json
import re
import stat
from pathlib import Path

from ..specialists import candidates

_FIELDS = frozenset({"schema_version", "project_id", "task_id", "attempt_id",
                     "goal", "evaluation", "protocol_ref", "data_manifest_sha256",
                     "steps", "step_timeout_seconds", "metric_maximize",
                     "code_provider", "code_model", "feedback_provider", "feedback_model"})
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}\Z")
_MODEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9_./:-]{0,127}\Z")
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_PROVIDERS = {"openai", "anthropic", "gemini", "openrouter"}
_CAP = 32 * 1024 * 1024


def _digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def preview_aide(plan: dict) -> dict:
    if not isinstance(plan, dict) or set(plan) != _FIELDS or plan.get("schema_version") != "aide-dev-preview-v1":
        raise ValueError("AIDE_PLAN_INVALID")
    for key in ("project_id", "task_id", "attempt_id"):
        if not isinstance(plan[key], str) or not _ID.fullmatch(plan[key]):
            raise ValueError("AIDE_ID_INVALID")
    for key in ("goal", "evaluation", "protocol_ref"):
        value = plan[key]
        if not isinstance(value, str) or not value.strip() or len(value) > 3000 or "\x00" in value:
            raise ValueError("AIDE_TASK_TEXT_INVALID")
    if not isinstance(plan["data_manifest_sha256"], str) or not _SHA.fullmatch(plan["data_manifest_sha256"]):
        raise ValueError("AIDE_DATA_MANIFEST_INVALID")
    if (type(plan["steps"]) is not int or not 1 <= plan["steps"] <= 5
            or type(plan["step_timeout_seconds"]) is not int
            or not 1 <= plan["step_timeout_seconds"] <= 120
            or type(plan["metric_maximize"]) is not bool):
        raise ValueError("AIDE_PILOT_BUDGET_INVALID")
    for key in ("code", "feedback"):
        if (not isinstance(plan[key + "_provider"], str) or plan[key + "_provider"] not in _PROVIDERS
                or not isinstance(plan[key + "_model"], str) or not _MODEL.fullmatch(plan[key + "_model"])):
            raise ValueError("AIDE_MODEL_INVALID")
    digest = _digest(json.dumps(plan, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode())
    task = (
        "DEV-only candidate algorithm search. Do not use reserved/confirmation data or write a manuscript.\n"
        "Goal: " + plan["goal"] + "\n"
        "Evaluation: " + plan["evaluation"] + "\n"
        "Use the exact declared independent evaluation protocol, legal features and matched baselines. "
        "Do not invent evidence, modify splits or optimize the evaluator. Return candidate code and journal; "
        "scientific review is external. Instructions do not enforce isolation.\n"
    )
    argv = ["aide", "data_dir=data", "desc_file=task.md", "log_dir=logs",
            "workspace_dir=workspaces", "exp_name=" + json.dumps(plan["attempt_id"]),
            "copy_data=true", "preprocess_data=false", "generate_report=false",
            "agent.data_preview=false", "agent.k_fold_validation=1",
            "agent.search.num_drafts=1", "agent.steps=" + str(plan["steps"]),
            "exec.timeout=" + str(plan["step_timeout_seconds"]),
            "agent.metric_maximize=" + str(plan["metric_maximize"]).lower()]
    for key in ("code", "feedback"):
        argv.extend(["agent." + key + ".provider=" + plan[key + "_provider"],
                     "agent." + key + ".model=" + json.dumps(plan[key + "_model"]),
                     "agent." + key + ".max_tokens=4096"])
    source = candidates("optimization")["candidates"][0]
    return {"status": "AIDE_PREVIEW_ONLY", "project_id": plan["project_id"],
            "task_id": plan["task_id"], "attempt_id": plan["attempt_id"],
            "upstream_revision": source["revision"], "plan_sha256": digest,
            "protocol_ref_declared": plan["protocol_ref"],
            "data_manifest_sha256_declared": plan["data_manifest_sha256"],
            "argv_preview": argv, "environment_preview": {"PYTHONUTF8": "1"}, "task_file_preview": task,
            "task_file_sha256": _digest(task.encode("utf-8")),
            "expected_artifacts": ["logs/<index>-" + plan["attempt_id"] + "/best_solution.py",
                                   "logs/<index>-" + plan["attempt_id"] + "/journal.json"],
            "required_host_checks": ["approved provider/model and cost ceiling", "pinned actual installation",
                                     "fresh isolated DEV-only data snapshot and exact protocol",
                                     "independent evaluator and process-tree/resource/network containment",
                                     "deny reserved data and unapproved egress; data_preview=false is not isolation"],
            "hard_total_budget_enforced": False, "execution_authorized": False,
            "execute_performed": False, "model_calls_requested": 0}


def _plain(path: Path, *, directory: bool) -> None:
    info = path.lstat()
    if (stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400
            or not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))):
        raise ValueError("AIDE_ARTIFACT_REDIRECT_OR_TYPE_INVALID")


def collect_aide(plan: dict, attempt_root: str | Path, run_name: str) -> dict:
    """Read two exact provider outputs; no execution, no journal parsing or claim."""
    preview = preview_aide(plan)
    if not isinstance(run_name, str) or not re.fullmatch(r"[0-9]{1,8}-" + re.escape(plan["attempt_id"]), run_name):
        raise ValueError("AIDE_RUN_NAME_MISMATCH")
    root = Path(attempt_root)
    if not root.is_absolute() or ".." in root.parts:
        raise ValueError("AIDE_ATTEMPT_ROOT_INVALID")
    for parent in reversed((root, *root.parents)):
        _plain(parent, directory=True)
    logs = root / "logs"
    run = logs / run_name
    _plain(logs, directory=True)
    _plain(run, directory=True)
    artifacts = []
    for name in ("best_solution.py", "journal.json"):
        path = run / name
        _plain(path, directory=False)
        with path.open("rb") as stream:
            data = stream.read(_CAP + 1)
        if not data or len(data) > _CAP:
            raise ValueError("AIDE_ARTIFACT_EMPTY_OR_OVERSIZE")
        artifacts.append({"ref": path.relative_to(root).as_posix(), "sha256": _digest(data),
                          "bytes": len(data)})
    raw = {"schema_version": "2.0", "project_id": plan["project_id"],
           "task_id": plan["task_id"], "agent_id": "aide", "attempt_id": plan["attempt_id"],
           "execution": {"status": "NEEDS_REVIEW", "budget_exhausted": False},
           "deliverables": {"code_refs": [artifacts[0]["ref"]], "run_refs": [],
                            "evidence_refs": [artifacts[1]["ref"]], "report_refs": []},
           "findings": [], "scientific_assessment": {"claim_status": "NOT_ASSESSED",
               "protocol_status": "NOT_ASSESSED", "outcome": "NOT_ASSESSED", "review_required": True},
           "unresolved_issues": ["Provider execution, plan binding, metrics and data legality unverified.",
                                 "AIDE best_solution.py can represent an unsuccessful node; latest workspace predictions may belong to a different node.",
                                 "Artifact refs relative to operator-selected attempt root; not original PD-RW Runs."],
           "next_action_candidates": ["Independently review original protocol and candidate code before any reuse."],
           "authorization_verified": False, "scientific_completion_verified": False}
    return {"status": "AIDE_ARTIFACT_BYTES_OBSERVED_ONLY", "plan_sha256_declared": preview["plan_sha256"],
            "artifacts": artifacts, "agent_result": raw, "execution_authorized": False,
            "process_completion_verified": False, "plan_binding_verified": False,
            "scientific_validity_verified": False, "model_calls_requested": 0}
