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
     "bounded_interface": "fixed public grouped regression via specialist-host",
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
