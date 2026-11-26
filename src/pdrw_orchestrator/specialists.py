"""Pinned specialist candidates. Discovery metadata is not readiness or merit."""
from __future__ import annotations

from copy import deepcopy

# GitHub metadata observed 2026-11-26. Commit-pinned review targets, not installs.
_CATALOG = (
    {"id": "aide", "repository": "WecoAI/aideml",
     "revision": "b39bb0e145e7785bcbc29e1b5d123f01d8f04c2c",
     "stars_observed": 1633, "license_declared": "MIT",
     "capabilities": ["code_experiment", "optimization"],
     "integration": "PREVIEW_AND_ARTIFACT_INTAKE_ONLY",
     "bounded_interface": "fixed public grouped regression or operator-staged DEV snapshot via specialist-host",
     "source_paths": ["README.md", "setup.py", "aide/utils/config.yaml", "aide/run.py", "aide/utils/config.py"],
     "limitations": ["Native metric search; group/temporal split requires independent evaluator.",
                     "Generated code and model calls require separate isolation and approval.",
                     "No measured scientific gain."]},
    {"id": "rdagent", "repository": "microsoft/RD-Agent",
     "revision": "484776c211e4fbbeef03e0ec00d6bbee7362a4f4",
     "stars_observed": 15504, "license_declared": "MIT",
     "capabilities": ["hypothesis", "experiment_design", "code_experiment"],
     "integration": "CUSTOM_SYNTHETIC_PREPARE_AND_INTAKE_ONLY",
     "bounded_interface": "fixed public grouped regression via specialist-host",
     "source_paths": ["README.md", "docs/scens/data_science.rst", "rdagent/app/data_science/loop.py", "rdagent/app/data_science/conf.py", "rdagent/app/cli.py", "rdagent/scenarios/data_science/scen/__init__.py", "rdagent/scenarios/data_science/test_eval.py", "rdagent/scenarios/data_science/dev/runner/eval.py", "rdagent/log/timer.py"],
     "limitations": ["Custom DataScienceScen supports native bounded loops; data sampling/evaluator and Docker dependencies need acceptance.",
                     "Native test evaluation injects answers into candidate workspace; no eval dataset in pilot.",
                     "No live execution, no measured scientific gain."]},
    {"id": "arc", "repository": "aiming-lab/AutoResearchClaw",
     "revision": "be4ba4755bf1b52220f25e13b2293b5956590070",
     "stars_observed": 14953, "license_declared": "MIT",
     "capabilities": ["discovery", "literature", "hypothesis", "experiment_design"],
     "integration": "DISCOVERY_PREVIEW_AND_INTAKE_ONLY",
     "bounded_interface": "public literature discovery stages 1-4 via specialist-host; not hypothesis or experiment execution",
     "source_paths": ["README.md", "researchclaw/cli.py", "researchclaw/pipeline/runner.py", "researchclaw/pipeline/stages.py", "researchclaw/pipeline/stage_impls/_literature.py", "researchclaw/pipeline/stage_impls/_topic.py"],
     "limitations": ["Full pipeline includes experiments and manuscript generation.",
                     "Only stages 1-4 previewed; startup/post-run effects and literature fallback require independent checks.",
                     "No live execution, no measured scientific gain."]},
    {"id": "tooluniverse", "repository": "mims-harvard/ToolUniverse",
     "revision": "23168a559128900f743be48f4094e4b99596f672",
     "stars_observed": 1809, "license_declared": "Apache-2.0",
     "capabilities": ["literature_lookup", "doi_lookup"],
     "integration": "OPT_IN_NATIVE_CROSSREF_CALL_NOT_LIVE_ACCEPTED",
     "bounded_interface": "public Crossref keyword/DOI metadata only",
     "source_paths": ["docs/guide/literature_search_tools_tutorial.rst", "src/tooluniverse/crossref_tool.py",
                      "src/tooluniverse/base_rest_tool.py", "src/tooluniverse/data/crossref_tools.json"],
     "limitations": ["Optional pinned install and explicit public network opt-in required.",
                     "No arbitrary tool execution, no LLM, no full text or novelty certification.",
                     "No live acceptance or measured scientific gain."]},
)


def candidates(capability: str | None = None) -> dict:
    if capability is not None and (not isinstance(capability, str) or
                                    not capability.strip() or len(capability) > 80):
        raise ValueError("SPECIALIST_CAPABILITY_INVALID")
    rows = []
    for record in _CATALOG:
        if capability is not None and capability not in record["capabilities"]:
            continue
        item = deepcopy(record)
        item.update({"source_url": "https://github.com/" + item["repository"] + "/tree/" + item["revision"],
                     "installed": None, "capability_accepted": False,
                     "execution_eligible": False, "scientific_gain_measured": False})
        rows.append(item)
    return {"status": "SPECIALIST_CANDIDATES_ONLY", "observed_as_of": "2026-11-26",
            "capability": capability, "candidates": rows,
            "selected_provider": None, "execution_authorized": False}

def recommend(task, *, scope, rules=()):
    """Select one task-fit candidate, not a runtime capability acceptance.

    Scope is a caller declaration. A provider that has not passed actual host
    acceptance remains ineligible for automatic dispatch.
    """
    from .models import TaskPacket
    from .policy import compile_guidance
    if not isinstance(task, TaskPacket):
        raise ValueError("SPECIALIST_TASK_REQUIRED")
    if scope not in ("public_topic", "public_synthetic", "staged_dev", "original_local"):
        raise ValueError("SPECIALIST_SCOPE_INVALID")
    role = task.capability or task.task_type
    chosen, alternatives, reason = None, [], "USE_GENERAL_HOST_SCIENTIFIC_JUDGMENT"
    if scope == "public_topic" and role in ("discovery", "literature"):
        chosen, reason = "arc", "PUBLIC_TOPIC_NATIVE_DISCOVERY_STAGES_1_TO_4"
    elif scope == "public_topic" and role in ("literature_lookup", "doi_lookup"):
        chosen, reason = "tooluniverse", "NARROW_METADATA_QUERY_WITHOUT_LLM"
    elif scope in ("public_synthetic", "staged_dev") and role in ("code_experiment", "optimization"):
        chosen, reason = "aide", "FIXED_METRIC_NATIVE_SEARCH"
        if scope == "public_synthetic" and role == "code_experiment":
            alternatives = ["rdagent"]
    elif scope == "public_synthetic" and role == "experiment_design":
        chosen, reason = "rdagent", "BOUNDED_SYNTHETIC_RD_ITERATION_ONLY"
    if chosen in ("arc", "tooluniverse") and task.task_type != "discovery":
        chosen, alternatives, reason = None, [], "NATIVE_TASK_TYPE_MISMATCH"
    if chosen == "aide" and task.task_type != "code_experiment":
        chosen, alternatives, reason = None, [], "NATIVE_TASK_TYPE_MISMATCH"
    if chosen == "rdagent" and task.task_type != "experiment_design":
        chosen, alternatives, reason = None, [], "NATIVE_TASK_TYPE_MISMATCH"
    # Scope/role alone cannot establish scientific adequacy or permissions.
    effects = list(task.required_effects)
    if chosen:
        effects = sorted(set(effects) | ({"network"} if chosen == "tooluniverse"
                      else {"network", "external_model"} if chosen == "arc"
                      else {"network", "external_model", "training"}))
    from dataclasses import replace
    guidance = compile_guidance(replace(task, required_effects=tuple(effects)), rules)
    if guidance.denied_effects:
        chosen, alternatives, reason = None, [], "LOCAL_POLICY_DENIED_EFFECT"
    if task.budget.get("max_model_calls") == 0 and chosen not in (None, "tooluniverse"):
        chosen, alternatives, reason = None, [], "NO_MODEL_CALL_BUDGET"
    return {"status": "SPECIALIST_ROUTE_PROPOSAL_ONLY", "project_id": task.project_id,
            "task_id": task.task_id, "scope_declared": scope, "capability": role,
            "recommended_candidate": chosen, "alternatives": alternatives,
            "reason": reason, "required_effects_for_review": effects,
            "guidance": guidance.to_dict(), "fallback": "PD-RW-Agent/general host",
            "execution_authorized": False, "capability_accepted": False,
            "can_auto_dispatch": False}
