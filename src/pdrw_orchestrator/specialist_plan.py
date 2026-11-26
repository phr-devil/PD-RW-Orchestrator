"""Compile an explicit scientific task into an existing specialist's native plan.

No new scientific decision, automatic effect inheritance, provider launch,
or source authorization. Native validation is delegated to existing adapters.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from . import aide_pilot, specialist_host
from .adapters.aide import preview_aide
from .adapters.arc import preview_arc
from .adapters import tooluniverse
from .models import TaskPacket
from .specialists import recommend

_OPTIONS = {
    "aide": {"attempt_id", "goal", "evaluation", "protocol_ref", "data_manifest_sha256",
             "steps", "step_timeout_seconds", "metric_maximize", "code_provider", "code_model",
             "feedback_provider", "feedback_model"},
    "arc": {"attempt_id", "public_topic", "research_scope", "max_papers", "config_sha256"},
    "tooluniverse": {"attempt_id", "operation", "public_text", "limit"},
}
_SCHEMAS = {"aide": "aide-dev-preview-v1", "arc": "arc-discovery-preview-v1",
            "tooluniverse": "tooluniverse-public-literature-v1"}


def _digest(value):
    return hashlib.sha256(aide_pilot._canonical(value)).hexdigest()


def compile_plan(task, scope, options, *, rules=(), prior=None, prior_root=None, review_ref=None):
    """Options contain explicitly approved-for-review provider-facing text.

    The task objective, evidence contents, grants and prior artifact bytes are
    never copied into the native provider-facing fields automatically.
    """
    if not isinstance(task, TaskPacket):
        raise ValueError("SPECIALIST_TASK_REQUIRED")
    if not isinstance(options, dict):
        raise ValueError("SPECIALIST_OPTIONS_OBJECT_REQUIRED")
    route = recommend(task, scope=scope, rules=rules)
    previous = None
    if any(x is not None for x in (prior, prior_root, review_ref)):
        if prior is None or prior_root is None or not isinstance(review_ref, str) or not review_ref.strip():
            raise ValueError("SPECIALIST_RELAY_INTAKE_ROOT_REVIEW_REQUIRED")
        old, raw = specialist_host.unpack_intake(prior)
        if old.project_id != task.project_id or old.task_id == task.task_id:
            raise ValueError("SPECIALIST_RELAY_TASK_IDENTITY_MISMATCH")
        if review_ref not in task.evidence_refs:
            raise ValueError("SPECIALIST_RELAY_REVIEW_REF_NOT_IN_NEXT_TASK")
        checked = specialist_host.verify_artifacts(prior, prior_root)
        previous = {"provider": prior["provider"], "task_id": old.task_id,
                    "attempt_id": raw["attempt_id"], "plan_sha256_declared": prior["plan_sha256_declared"],
                    "intake_sha256": _digest(prior),
                    "artifact_observation": checked,
                    "independent_review_ref_declared": review_ref,
                    "review_contents_verified": False, "original_authorization_inherited": False}
    chosen = route["recommended_candidate"]
    result = {"schema_version": "specialist-plan-compilation-v1",
              "project_id": task.project_id, "task_id": task.task_id,
              "task_sha256": _digest(task.to_dict()), "route": route,
              "previous": previous, "native_plan": None, "native_plan_sha256": None,
              "execution_authorized": False, "can_auto_dispatch": False,
              "scientific_transition_verified": False, "model_calls_requested": 0}
    if chosen is None:
        return {**result, "status": "GENERAL_HOST_OR_BLOCKED", "next": "Review route reason; use existing original-source workflow."}
    if scope == "public_synthetic":
        # Fixed fixture constructors own their data, protocol and task IDs.
        # Do not pretend that a generic task may replace them.
        return {**result, "status": "FIXED_PILOT_PREPARATION_REQUIRED",
                "next": "Use aide-pilot prepare or rdagent-pilot prepare for the selected fixed engineering task."}
    if chosen not in _OPTIONS or set(options) != _OPTIONS[chosen]:
        raise ValueError("SPECIALIST_NATIVE_OPTIONS_INVALID")
    plan = {"schema_version": _SCHEMAS[chosen], "project_id": task.project_id,
            "task_id": task.task_id, **options}
    if chosen == "aide":
        if scope != "staged_dev" or task.task_type != "code_experiment":
            raise ValueError("SPECIALIST_AIDE_TASK_TYPE_OR_SCOPE_MISMATCH")
        if plan["protocol_ref"] not in task.protocol_refs:
            raise ValueError("SPECIALIST_AIDE_PROTOCOL_NOT_IN_TASK")
        checked = preview_aide(plan)
        command = "aide-dev stage"
    elif chosen == "arc":
        if scope != "public_topic" or task.task_type != "discovery":
            raise ValueError("SPECIALIST_ARC_TASK_TYPE_OR_SCOPE_MISMATCH")
        checked = preview_arc(plan)
        command = "specialist-host prepare --provider arc"
    else:
        if scope != "public_topic" or task.task_type != "discovery":
            raise ValueError("SPECIALIST_TOOLUNIVERSE_TASK_TYPE_OR_SCOPE_MISMATCH")
        expected = "doi" if task.capability == "doi_lookup" else "search"
        if plan["operation"] != expected:
            raise ValueError("SPECIALIST_TOOLUNIVERSE_CAPABILITY_MISMATCH")
        checked = tooluniverse.preview(plan, rules)
        if checked["blocked_by_policy"]:
            raise ValueError("SPECIALIST_NATIVE_POLICY_DENIED")
        command = "tooluniverse preview"
    return {**result, "status": "NATIVE_PLAN_COMPILED_REVIEW_REQUIRED", "native_plan": plan,
            "native_plan_sha256": checked["plan_sha256"], "next": command,
            "host_review": ["Compare explicit provider-facing text to the actual scoped task.",
                            "Check original author choices, existing grants, applicable guidance and actual host budgets.",
                            "Review prior artifacts and original evidence; byte matching is not scientific validation.",
                            "Keep local task, review references and prior outputs out of the external request unless separately approved."]}


def export_plan(compiled, path):
    if compiled.get("status") != "NATIVE_PLAN_COMPILED_REVIEW_REQUIRED" or compiled.get("native_plan") is None:
        raise ValueError("SPECIALIST_NO_NATIVE_PLAN_TO_EXPORT")
    path = aide_pilot._check_root(path, exists=False)
    aide_pilot._write(path, (json.dumps(compiled["native_plan"], ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    return str(path)
