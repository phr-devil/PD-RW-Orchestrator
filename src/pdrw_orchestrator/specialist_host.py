"""Native specialist -> existing authorized host -> existing advise interface.

No subprocess, model call, new grant, scheduler, or scientific decision engine.
The host must establish permissions and effective containment outside this code.
"""
from __future__ import annotations

import copy
import hashlib
import math
import re
from pathlib import Path

from . import aide_pilot, aide_dev
from .adapters import rdagent
from .adapters.aide import collect_aide, _plain, preview_aide
from .adapters.aide_install import inspect_specialist_install
from .adapters.arc import collect_arc, preview_arc, discovery_config_issues
from .agent_result import normalize_result
from .models import TaskPacket
from .policy import compile_guidance
from .specialists import candidates

_PROVIDERS = ("aide", "rdagent", "arc")
_ARTIFACT_FIELDS = ("code_refs", "run_refs", "report_refs", "evidence_refs")


def _context(provider, root, plan=None):
    if provider not in _PROVIDERS:
        raise ValueError("UNKNOWN_SPECIALIST_PROVIDER")
    root = aide_pilot._check_root(root, exists=True)
    if provider == "arc":
        if plan is None:
            raise ValueError("ARC_PLAN_REQUIRED")
        native = preview_arc(plan)
        task = TaskPacket(project_id=plan["project_id"], task_id=plan["task_id"],
                          task_type="discovery", capability="literature",
                          objective=plan["public_topic"] + "\n" + plan["research_scope"],
                          required_effects=("external_model", "network"))
        cwd = root
    elif provider in ("aide", "rdagent") and plan is not None:
        native = aide_dev.verify(root, plan) if provider == "aide" else rdagent.verify_dev(root, plan)
        task = TaskPacket(project_id=plan["project_id"], task_id=plan["task_id"],
                          task_type="code_experiment", capability="research_iteration" if provider == "rdagent" else "code_experiment",
                          objective=plan["goal"], protocol_refs=(plan["protocol_ref"],),
                          required_effects=("external_model", "network", "training"))
        cwd = root / "worker"
    else:
        if plan is not None:
            raise ValueError("PILOT_PLAN_IS_ALREADY_PREPARED")
        native = aide_pilot.verify(root) if provider == "aide" else rdagent.verify(root)
        plan = native["plan"]
        task = TaskPacket(project_id=plan["project_id"], task_id=plan["task_id"],
                          task_type="code_experiment", capability="code_experiment",
                          objective="Fixed public synthetic grouped sensor regression; candidate code and independent RMSE.",
                          protocol_refs=(plan.get("protocol_ref", "AIDE-SYNTHETIC-GROUP-RMSE-V1"),),
                          required_effects=("external_model", "network", "training"))
        cwd = root / "worker"
    return root, cwd, plan, native, task


def _config_observation(path, declared):
    # Only exact, operator-selected config files. Never print raw contents or
    # the actual digest of a mismatched file, which could contain credentials.
    try:
        raw = aide_pilot._read(path, 128 * 1024)
    except (OSError, ValueError):
        return "MISSING_OR_UNSAFE"
    return "DECLARED_BYTES_MATCH" if hashlib.sha256(raw).hexdigest() == declared else "DECLARED_BYTES_MISMATCH"


def prepare(provider, root, *, plan=None, source_root=None, rules=()):
    root, cwd, plan, native, task = _context(provider, root, plan)
    guidance = compile_guidance(task, rules)
    blockers = []
    source = None
    if source_root is None:
        blockers.append("SELECTED_SOURCE_NOT_CHECKED")
    else:
        source = inspect_specialist_install(provider, source_root)
        if source["status"] != "PINNED_SELECTED_BYTES_MATCH":
            blockers.append("PINNED_SELECTED_SOURCE_NOT_MATCHED")
    config = "NOT_APPLICABLE_TO_AIDE_CLI_PLAN"
    if provider == "arc":
        config = _config_observation(cwd / "config.arc.yaml", plan["config_sha256"])
        if config == "DECLARED_BYTES_MATCH":
            raw_config = aide_pilot._read(cwd / "config.arc.yaml", 128 * 1024)
            if hashlib.sha256(raw_config).hexdigest() != plan["config_sha256"]:
                blockers.append("PROVIDER_CONFIG_NOT_MATCHED")
            else:
                blockers.extend(discovery_config_issues(raw_config, plan["max_papers"]))
        if any((cwd / name).exists() or (cwd / name).is_symlink() for name in ("run", "kb")):
            blockers.append("OUTPUT_ALREADY_EXISTS_RECONCILE")
    elif provider == "rdagent":
        # Native app/cli.py loads .env in cwd before initializing settings.
        # Environment precedence can still override file values.
        config = _config_observation(cwd / ".env", plan["provider_config_sha256_declared"])
        if {p.name for p in cwd.iterdir()} - {"ds_data", ".env"}:
            blockers.append("WORKER_NOT_FRESH_RECONCILE")
    else:
        if {p.name for p in cwd.iterdir()} - {"data", "task.md"}:
            blockers.append("WORKER_NOT_FRESH_RECONCILE")
    if config in ("MISSING_OR_UNSAFE", "DECLARED_BYTES_MISMATCH"):
        blockers.append("PROVIDER_CONFIG_NOT_MATCHED")
    if guidance.denied_effects:
        blockers.append("LOCAL_POLICY_EFFECT_DENIED")
    candidate = next(row for row in candidates()["candidates"] if row["id"] == provider)
    return {
        "schema_version": "specialist-host-handoff-v1",
        "status": "HOST_PREPARATION_BLOCKED" if blockers else "HOST_REVIEW_REQUIRED",
        "provider": provider, "upstream_revision": candidate["revision"],
        "task": task.to_dict(), "attempt_id": plan["attempt_id"],
        "plan_sha256": native["plan_sha256"],
        "local_cwd": str(cwd), "argv": native["argv_preview"],
        "environment_overrides": native.get("environment_preview", {}),
        "source_observation": source, "config_observation": config,
        "guidance": guidance.to_dict(), "blockers": blockers,
        "required_host_checks": native["required_host_checks"] + (["Actual DEV scope and external transmission are not proven by snapshot hashes; authenticate original H6/DEV permission, data classification and original protocol. Independent project-specific evaluator and replay are required."] if native["status"] in ("DECLARED_DEV_SNAPSHOT_BYTES_MATCH_ONLY", "RDAGENT_DECLARED_DEV_SNAPSHOT_BYTES_MATCH_ONLY") else []),
        "host_instruction": [
            "Read this local packet once; do not pass it wholesale to the model or external provider.",
            "Resolve listed blockers. Authenticate existing original scope or obtain only genuinely new grants; no hash or packet grants permission.",
            "Check pinned executable/interpreter/dependencies, effective config, allowed data and approved model/network/compute budgets in the existing trusted host.",
            "Review required guidance and resolve conflicts with the native task before launch; do not silently alter frozen evaluation or task bytes.",
            "If authorized and contained, invoke the native argv directly from local_cwd using the selected environment. Do not execute a shell string or retry an uncertain job.",
            "Record actual exit/attempt/usage and native outputs. Use specialist-host collect, then advise --intake-file; independently review before any scientific claim or downstream task."
        ],
        "execution_authorized": False, "execute_performed": False,
        "host_isolation_verified": False, "effective_config_verified": False,
        "model_calls_requested": 0,
    }


def collect(provider, root, *, plan=None, run_name=None, score_replay=False):
    root, cwd, plan, native, task = _context(provider, root, plan)
    if score_replay and (provider == "arc" or native["status"] in ("DECLARED_DEV_SNAPSHOT_BYTES_MATCH_ONLY", "RDAGENT_DECLARED_DEV_SNAPSHOT_BYTES_MATCH_ONLY")):
        raise ValueError("SCORING_ONLY_FOR_ALGORITHM_PILOTS")
    if provider == "aide":
        if not run_name:
            raise ValueError("AIDE_RUN_NAME_REQUIRED")
        observed = collect_aide(plan, cwd, run_name)
        prefix = "worker/"
    elif provider == "rdagent":
        if run_name is not None:
            raise ValueError("RUN_NAME_ONLY_FOR_AIDE")
        observed = rdagent.collect(root, plan if native["status"] == "RDAGENT_DECLARED_DEV_SNAPSHOT_BYTES_MATCH_ONLY" else None)
        prefix = ""
    else:
        if run_name is not None:
            raise ValueError("RUN_NAME_ONLY_FOR_AIDE")
        observed = collect_arc(plan, root / "run")
        prefix = "run/"
    if observed["plan_sha256_declared"] != native["plan_sha256"]:
        raise ValueError("SPECIALIST_PLAN_DIGEST_MISMATCH")
    raw = copy.deepcopy(observed["agent_result"])
    for name in _ARTIFACT_FIELDS:
        raw["deliverables"][name] = [prefix + ref for ref in raw["deliverables"][name]]
    artifacts = [{**a, "ref": prefix + a["ref"]} for a in observed["artifacts"]]
    # Carry useful native observations without treating them as findings.
    provider_summary = None
    if provider == "arc":
        provider_summary = {key: observed[key] for key in (
            "candidate_count", "declared_placeholder_count", "real_search_reported")}
    elif score_replay:
        scored = aide_pilot.score(root) if provider == "aide" else rdagent.score(root)
        if scored["plan_sha256"] != native["plan_sha256"]:
            raise ValueError("SPECIALIST_SCORE_PLAN_MISMATCH")
        provider_summary = {key: scored[key] for key in (
            "prediction_sha256", "rows", "independent_group_count", "metric",
            "candidate_rmse", "linear_baseline_rmse", "mean_baseline_rmse",
            "delta_candidate_minus_linear", "group_scores")}
    # Bind the scored replay prediction bytes to the observed artifact set.
    if score_replay:
        prediction_ref = "review/submission.csv"
        existing = next((a for a in artifacts if a["ref"] == prediction_ref), None)
        if existing is None:
            raw_prediction = aide_pilot._read(root / prediction_ref, aide_pilot._MAX_PRED_BYTES)
            existing = {"ref": prediction_ref, "sha256": hashlib.sha256(raw_prediction).hexdigest(), "bytes": len(raw_prediction)}
            artifacts.append(existing)
            raw["deliverables"]["evidence_refs"].append(prediction_ref)
        if existing["sha256"] != provider_summary["prediction_sha256"]:
            raise ValueError("SPECIALIST_REPLAY_PREDICTION_DIGEST_MISMATCH")
    # These are adapter byte observations, not trusted process or Run receipts.
    normalize_result(raw, task)
    return {"schema_version": "specialist-intake-v1", "provider": provider,
            "task": task.to_dict(), "agent_result": raw,
            "plan_sha256_declared": native["plan_sha256"],
            "artifact_observation": {"status": observed["status"], "artifacts": artifacts,
                "artifact_ref_base": "OPERATOR_SELECTED_ISOLATED_ATTEMPT_ROOT",
                "provider_summary": provider_summary,
                "process_completion_verified": False, "plan_binding_verified": False,
                "scientific_validity_verified": False},
            "execution_authorized": False}


def unpack_intake(value):
    """Only consume task and self-report. All observation metadata stays untrusted."""
    if not isinstance(value, dict) or value.get("schema_version") != "specialist-intake-v1":
        raise ValueError("SPECIALIST_INTAKE_SCHEMA_INVALID")
    if set(value) != {"schema_version", "provider", "task", "agent_result",
                      "plan_sha256_declared", "artifact_observation", "execution_authorized"}:
        raise ValueError("SPECIALIST_INTAKE_FIELDS_INVALID")
    provider = value["provider"]
    if provider not in (*_PROVIDERS, "tooluniverse") or value["execution_authorized"] is not False:
        raise ValueError("SPECIALIST_INTAKE_PROVIDER_OR_AUTH_INVALID")
    task = TaskPacket(**value["task"])
    raw = value["agent_result"]
    if (not isinstance(raw, dict) or raw.get("schema_version") != "2.0"
            or raw.get("agent_id") != provider
            or not isinstance(raw.get("execution"), dict)
            or raw["execution"].get("status") != "NEEDS_REVIEW"):
        raise ValueError("SPECIALIST_INTAKE_RESULT_INVALID")
    normalized = normalize_result(raw, task)
    observation = value["artifact_observation"]
    digest = value["plan_sha256_declared"]
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ValueError("SPECIALIST_INTAKE_DIGEST_INVALID")
    if (not isinstance(observation, dict)
            or set(observation) - {"status", "artifacts", "artifact_ref_base",
                                    "provider_summary", "process_completion_verified",
                                    "plan_binding_verified", "scientific_validity_verified"}
            or observation.get("artifact_ref_base") != "OPERATOR_SELECTED_ISOLATED_ATTEMPT_ROOT"
            or any(observation.get(key) is not False for key in (
                "process_completion_verified", "plan_binding_verified", "scientific_validity_verified"))):
        raise ValueError("SPECIALIST_OBSERVATION_INVALID")
    artifacts = observation.get("artifacts")
    if not isinstance(artifacts, list) or not 1 <= len(artifacts) <= 32:
        raise ValueError("SPECIALIST_ARTIFACTS_INVALID")
    refs = set()
    for item in artifacts:
        if not isinstance(item, dict) or set(item) != {"ref", "sha256", "bytes"}:
            raise ValueError("SPECIALIST_ARTIFACT_INVALID")
        ref = item["ref"]
        if (not isinstance(ref, str) or not 1 <= len(ref) <= 300
                or not re.fullmatch(r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*", ref)
                or any(part in (".", "..") for part in ref.split("/")) or ref in refs
                or not isinstance(item["sha256"], str)
                or not re.fullmatch(r"[0-9a-f]{64}", item["sha256"])
                or type(item["bytes"]) is not int or not 1 <= item["bytes"] <= 32*1024*1024):
            raise ValueError("SPECIALIST_ARTIFACT_INVALID")
        refs.add(ref)
    declared_refs = {ref for name in _ARTIFACT_FIELDS for ref in normalized["deliverables"][name]}
    if normalized["deliverables"]["run_refs"] or declared_refs != refs:
        raise ValueError("SPECIALIST_ARTIFACT_REFERENCE_MISMATCH")
    return task, raw


def review_metadata(value):
    """Return only bounded observation fields; never accept caller attestations."""
    observation = value["artifact_observation"]
    provider = value["provider"]
    summary = observation.get("provider_summary")
    safe_summary = None
    if summary is not None:
        if not isinstance(summary, dict):
            raise ValueError("SPECIALIST_PROVIDER_SUMMARY_INVALID")
        if provider == "arc":
            count, placeholders = summary.get("candidate_count"), summary.get("declared_placeholder_count")
            real = summary.get("real_search_reported")
            if (type(count) is not int or not 0 <= count <= 1000
                    or type(placeholders) is not int or not 0 <= placeholders <= count
                    or type(real) is not bool):
                raise ValueError("SPECIALIST_ARC_SUMMARY_INVALID")
            safe_summary = {"candidate_count": count, "declared_placeholder_count": placeholders,
                            "real_search_reported": real, "literature_verified": False}
        elif provider == "tooluniverse":
            count, returned, total = (summary.get(k) for k in ("candidate_count", "returned_count", "total_count_reported"))
            if (type(count) is not int or type(returned) is not int or not 0 <= count <= returned <= 20
                    or (total is not None and (type(total) is not int or total < returned))):
                raise ValueError("SPECIALIST_TOOLUNIVERSE_SUMMARY_INVALID")
            kind = summary.get("record_kind", "literature")
            if kind not in ("literature", "dataset"):
                raise ValueError("SPECIALIST_TOOLUNIVERSE_KIND_INVALID")
            safe_summary = {"candidate_count": count, "returned_count": returned,
                            "total_count_reported": total, "literature_verified": False}
            if kind == "dataset":
                safe_summary.update({"record_kind": "dataset", "dataset_scope_verified": False,
                                     "license_verified": False, "suitability_verified": False})
        else:
            numeric = ("candidate_rmse", "linear_baseline_rmse", "mean_baseline_rmse",
                       "delta_candidate_minus_linear")
            if (summary.get("rows") != 48 or summary.get("independent_group_count") != 4
                    or summary.get("metric") != "RMSE"
                    or not isinstance(summary.get("prediction_sha256"), str)
                    or not re.fullmatch(r"[0-9a-f]{64}", summary["prediction_sha256"])
                    or any(type(summary.get(k)) not in (int, float) or
                           not math.isfinite(summary[k]) or abs(summary[k]) > 2e6 for k in numeric)):
                raise ValueError("SPECIALIST_SCORE_SUMMARY_INVALID")
            safe_summary = {k: summary[k] for k in (*numeric, "rows", "independent_group_count",
                                                    "metric", "prediction_sha256")}
            safe_summary.update({"prediction_origin_verified": False, "candidate_code_binding_verified": False})
            # Group details remain in the private original intake.
    return {"origin": "UNTRUSTED_SPECIALIST_INTAKE_FILE", "provider": provider,
            "plan_sha256_declared": value["plan_sha256_declared"],
            "artifact_ref_base": observation["artifact_ref_base"],
            "artifacts": observation["artifacts"], "provider_summary": safe_summary,
            "artifact_bytes_reverified_by_advise": False, "authorization_verified": False,
            "scientific_validity_verified": False}


def verify_artifacts(value, root):
    """Rehash exact observed files in a selected immutable attempt root.

    The caller must ensure the root is an approved isolated snapshot; byte
    equality cannot establish native process, scientific truth or authorization.
    """
    unpack_intake(value)
    review_metadata(value)
    root = aide_pilot._check_root(root, exists=True)
    items = value["artifact_observation"]["artifacts"]
    if sum(item["bytes"] for item in items) > 128 * 1024 * 1024:
        raise ValueError("SPECIALIST_ARTIFACT_TOTAL_CAP_EXCEEDED")
    for item in items:
        path = root / item["ref"]
        for parent in reversed(tuple(p for p in path.parents if p != root and root in p.parents)):
            _plain(parent, directory=True)
        _plain(path, directory=False)
        stat = path.stat()
        if stat.st_nlink != 1 or stat.st_size != item["bytes"]:
            raise ValueError("SPECIALIST_ARTIFACT_SIZE_OR_LINK_MISMATCH")
        h = hashlib.sha256()
        remaining = item["bytes"]
        with path.open("rb") as stream:
            while remaining:
                chunk = stream.read(min(remaining, 1024 * 1024))
                if not chunk:
                    raise ValueError("SPECIALIST_ARTIFACT_BYTES_MISMATCH")
                h.update(chunk)
                remaining -= len(chunk)
            if stream.read(1) or h.hexdigest() != item["sha256"]:
                raise ValueError("SPECIALIST_ARTIFACT_BYTES_MISMATCH")
    return {"status": "INTAKE_ARTIFACT_BYTES_MATCH_ONLY", "artifact_count": len(items),
            "total_bytes": sum(x["bytes"] for x in items), "artifact_bytes_reverified": True,
            "scientific_validity_verified": False, "process_completion_verified": False,
            "authorization_verified": False}


def scientific_review_focus(metadata):
    """A compact provider-specific review objective, not another decision engine."""
    provider = metadata["provider"]
    summary = metadata.get("provider_summary") or {}
    if provider == "tooluniverse" and summary.get("record_kind") == "dataset":
        return ("Compare the most promising candidate datasets by actual license, accessible bytes, "
                "independent units, ground-truth labels, condition coverage, observation legality "
                "and nearest published use. Metadata is not proof of suitability. Identify a data "
                "path that could distinguish the proposed scientific claim, or the single missing "
                "premise; UNKNOWN is not a negative. Preserve original H4 selection.")
    if provider in ("tooluniverse", "arc"):
        prefix = ""
        if provider == "arc" and (summary.get("real_search_reported") is False or
                summary.get("declared_placeholder_count", 0) > 0):
            prefix = "Do not treat placeholder/fallback records as literature. "
        return (prefix + "Verify named closest original papers (not just metadata) under matched "
                "legal information and evaluation; state concrete unresolved gap, strongest competing "
                "explanation and the minimum discriminating evidence. Distinguish unsearched from absent "
                "work. Compare distinct credible opportunities and paper/reuse value in the original "
                "H3 workflow; do not select a topic for the author.")
    if provider in ("aide", "rdagent"):
        return ("Independently inspect complete selected code, legal data/splits, matched strong "
                "baselines and original evaluator/replay. Native scores and replay-file scores alone "
                "do not prove valid science. Separate invalid, not-run, inconclusive, valid negative "
                "and bounded positive results. Compare named nearest work and actual new knowledge, "
                "including reliability/measurement boundaries or useful negative findings. Reuse existing "
                "evidence; if a credible contribution exists, identify only its decisive remaining gap. "
                "Otherwise compare a genuinely different legal information lever and cheapest discriminating "
                "probe. Preserve H6/H8 scope; no automatic manuscript, publication or new training.")
    raise ValueError("SPECIALIST_REVIEW_PROVIDER_INVALID")
