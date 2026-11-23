"""Non-executable next-task proposals. Never inherit previous task effects or grants."""
from __future__ import annotations
import hashlib
from typing import Any
from .models import TaskPacket

_OBJECTIVES = {
    "INDEPENDENT_REVIEW": ("review", "review",
        "Independently assess the previous result against the original protocol, actual artifacts, baselines and scientific claim; record gaps and limitations."),
    "RECONCILE": ("reconciliation", "review",
        "Reconcile original project identity, evidence references and uncertain prior execution in read-only mode; do not restart or revise experiments."),
    "VERIFY_EXISTING_SCOPE": ("scope_review", "review",
        "Check original user authorization and frozen project scope for the requested effects; distinguish existing grant, new-grant requirement and denial."),
    "REQUEST_AUTHOR_DECISION": ("scope_review", "review",
        "Prepare a concise author decision request tied to the original source and actual proposed new operation; take no protected action."),
    "HOLD": ("scope_review", "review",
        "Document the exact blocking policy/scope conflict and identify any independently permitted read-only actions."),
    "REVISE_PLAN": ("experiment_design", "hypothesis",
        "Investigate why the previous task failed and propose a decision-relevant alternative or repair without running experiments."),
    "SWITCH_AGENT": ("routing_review", "review",
        "Assess whether a suitable, actually available specialist can take over the previous task under its original constraints; do not dispatch."),
    "CONTINUE_SAME_AGENT": ("planning", "review",
        "Verify which remaining in-scope steps justify continuation with the same agent; do not implicitly repeat the previous task."),
    "READY_FOR_NEXT_STAGE": ("planning", "review",
        "Review verified completion evidence and identify the next authorized scientific stage without starting it."),
    "REVIEW_OUTCOME_PENDING": ("human_assessment", "human_review",
        "Await trusted original-evidence assessment of the completed review; do not send another agent merely to re-review the same report."),
}

_ACCEPTANCE = (
    "Report original project/task identity, cited source and artifact refs, what is verified versus unverified, "
    "relevant method constraints, explicit unresolved blockers and evidence-backed next-action options.",
)
_STOP = (
    "Stop if original evidence or scope cannot be verified, any protected action is required, or the decision-relevant review is complete.",
)

def propose_next_task(previous: TaskPacket, normalized: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    """Return a bounded read-only proposal. Agent-reported refs are NOT verified inputs."""
    kind = decision.get("decision_type")
    if kind not in _OBJECTIVES:
        raise ValueError("UNKNOWN_NEXT_ACTION")
    if decision.get("project_id") != previous.project_id or decision.get("from_task_id") != previous.task_id:
        raise ValueError("NEXT_TASK_IDENTITY_MISMATCH")
    if normalized.get("task_id") != previous.task_id or normalized.get("project_id") != previous.project_id:
        raise ValueError("NEXT_TASK_RESULT_IDENTITY_MISMATCH")
    task_type, capability, objective = _OBJECTIVES[kind]
    if kind == "SWITCH_AGENT":
        capability = previous.capability or previous.task_type
        objective = (
            "Identify a VERIFIED alternative provider for the original "
            + previous.task_type + " task under the original scope; "
            "do not repeat the work or dispatch automatically."
        )
    # Attempt and decision-specific stable proposal identity prevents branch
    # collisions without copying unbounded old task IDs into new identifiers.
    identity = "|".join((
        previous.project_id, previous.task_id,
        str(normalized.get("attempt_id", "UNSPECIFIED")), kind,
    ))
    proposal_id = "NEXT-" + kind[:12] + "-" + hashlib.sha256(
        identity.encode("utf-8")).hexdigest()[:12]
    claimed_refs = {k: list(v) for k, v in normalized.get("deliverables", {}).items()}
    return {
        "schema_version": "1.0",
        "status": "PROPOSED_SOURCE_REVIEW_REQUIRED",
        "proposal_id": proposal_id,
        "project_id": previous.project_id,
        "from_task_id": previous.task_id,
        "decision_type": kind,
        "task_type": task_type,
        "capability": capability,
        "objective": objective,
        "acceptance_criteria": list(_ACCEPTANCE),
        "stop_conditions": list(_STOP),
        "original_protocol_refs": list(previous.protocol_refs),
        "original_evidence_refs": list(previous.evidence_refs),
        "unverified_agent_artifact_refs": claimed_refs,
        "prior_authorization_refs_unverified": list(previous.authorization_refs),
        "prior_effects_for_scope_review_only": list(previous.required_effects),
        "required_effects": [],
        "budget": {},
        "authorization_verified": False,
        "scientific_completion_verified": False,
        "can_dispatch": False,
    }

def policy_task_for_proposal(proposal: dict[str, Any]) -> TaskPacket:
    """Compile next-task guidance by its own task type, not the previous task."""
    return TaskPacket(
        task_id=proposal["proposal_id"], project_id=proposal["project_id"],
        task_type=proposal["task_type"], objective=proposal["objective"],
        capability=proposal["capability"],
    )
