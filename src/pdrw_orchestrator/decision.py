"""Candidate next actions, not science verdicts or grants."""
from __future__ import annotations
from typing import Any

from .models import TaskPacket
from .next_task import propose_next_task
from .policy import GuidancePacket
from .registry import AgentSpec

DECISION_TYPES = frozenset({
    "CONTINUE_SAME_AGENT", "SWITCH_AGENT", "INDEPENDENT_REVIEW",
    "REVISE_PLAN", "REQUEST_AUTHOR_DECISION", "VERIFY_EXISTING_SCOPE",
    "RECONCILE", "HOLD", "READY_FOR_NEXT_STAGE", "REVIEW_OUTCOME_PENDING",
})
AUTH_STATES = frozenset({"SCOPE_NOT_YET_VERIFIED", "DENIED", "EXISTING_GRANT_VERIFIED",
                          "NEW_GRANT_REQUIRED", "NOT_REQUIRED_FOR_PROPOSAL"})

def _real_candidates(capability: str, agents: tuple[AgentSpec, ...], exclude: str | None = None) -> tuple[list[str], list[str]]:
    relevant = sorted((a for a in agents if capability in a.capabilities and a.id != exclude),
                      key=lambda a: (a.priority, a.id))
    ready = [a.id for a in relevant if a.verified_ready and a.adapter != "mock"]
    unavailable = [a.id for a in relevant if a.id not in ready]
    return ready, unavailable

def _source_blocker(context: dict | None, project_id: str) -> tuple[str, str] | None:
    """Only add blockers; no ordinary JSON can authenticate an existing grant."""
    if context is None:
        return None
    if not isinstance(context, dict) or context.get("project_id") != project_id:
        return ("RECONCILE", "SOURCE_PROJECT_ID_MISMATCH")
    if context.get("bridge_status") != "SOURCE_REVIEW_ONLY":
        return ("RECONCILE", "UPSTREAM_SOURCE_UNAVAILABLE")
    if (context.get("source_chain_status") is not None
            and context["source_chain_status"] != "SOURCE_READ_ONLY_CHECKS_COMPLETE"):
        return ("RECONCILE", "ORIGINAL_SOURCE_CHECK_REQUIRES_RECONCILIATION")
    if (context.get("operational_reconciliation_required") or
        context.get("unresolved_operation_count", 0)):
        return ("RECONCILE", "SOURCE_OPERATION_RECONCILIATION_REQUIRED")
    status = context.get("source_status")
    if status in ("NEEDS_RECONCILIATION", "NEEDS_OPERATIONAL_RECONCILIATION") or (
        isinstance(status, str) and status.startswith("BLOCKED_")
    ):
        return ("RECONCILE", "SOURCE_RECONCILIATION_REQUIRED")
    if status == "ARTIFACT_REVIEW_PENDING" or context.get("pending_scientific_review_count", 0):
        return ("INDEPENDENT_REVIEW", "SOURCE_ARTIFACT_REVIEW_PENDING")
    if status != "SOURCE_REVIEW_REQUIRED":
        return ("RECONCILE", "UNKNOWN_SOURCE_STATUS")
    return None

def decide_next(
    task: TaskPacket, normalized: dict[str, Any], guidance: GuidancePacket,
    agents: tuple[AgentSpec, ...], *, source_context: dict | None = None,
) -> dict:
    if normalized.get("project_id") != task.project_id or normalized.get("task_id") != task.task_id:
        raise ValueError("DECISION_TASK_IDENTITY_MISMATCH")
    if normalized.get("schema_version") != "2.0" or normalized.get("origin") != "UNTRUSTED_AGENT_OUTPUT":
        raise ValueError("UNVERIFIED_NORMALIZED_RESULT_REQUIRED")
    execution = normalized.get("execution", {})
    status = execution.get("reported_status")
    if not isinstance(status, str):
        raise ValueError("INVALID_NORMALIZED_RESULT")
    if normalized.get("scientific_assessment", {}).get("effective_claim_status") != "NOT_ASSESSED":
        raise ValueError("UNEXPECTED_TRUST_ESCALATION")

    blocker = _source_blocker(source_context, task.project_id)
    auth_status = ("DENIED" if guidance.denied_effects else
                   "SCOPE_NOT_YET_VERIFIED" if task.required_effects or status == "BLOCKED_AUTH" else
                   "NOT_REQUIRED_FOR_PROPOSAL")
    reasons: list[str]
    if blocker and blocker[0] == "RECONCILE":
        kind, reasons = blocker[0], [blocker[1]]
    elif guidance.denied_effects or status == "BLOCKED_POLICY":
        kind, reasons = "HOLD", ["POLICY_EFFECT_DENIED" if guidance.denied_effects else status]
    elif status == "BLOCKED_AUTH":
        kind, reasons = "VERIFY_EXISTING_SCOPE", [status]
    elif blocker:
        kind, code = blocker
        if kind == "INDEPENDENT_REVIEW" and task.task_type in ("review", "human_assessment"):
            kind = "REVIEW_OUTCOME_PENDING"
        reasons = [code]
    elif status in ("DEMO_ONLY", "BLOCKED_DEPENDENCY"):
        kind, reasons = "RECONCILE", ["MOCK_RESULT_NO_SCIENCE" if status == "DEMO_ONLY" else "DEPENDENCY_NOT_RESOLVED"]
    elif status == "NOT_CONNECTED":
        kind, reasons = "SWITCH_AGENT", ["PREVIOUS_AGENT_NOT_CONNECTED"]
    elif status == "FAILED":
        kind, reasons = "REVISE_PLAN", ["EXECUTION_FAILED_CAUSE_UNVERIFIED"]
    elif execution.get("budget_exhausted"):
        kind, reasons = "REVISE_PLAN", ["BUDGET_EXHAUSTED_NO_AUTO_RETRY"]
    elif status == "NEEDS_REVIEW":
        if task.task_type in ("review", "human_assessment"):
            kind, reasons = "REVIEW_OUTCOME_PENDING", ["REVIEW_REQUIRES_TRUSTED_EVIDENCE_ASSESSMENT"]
        else:
            kind, reasons = "INDEPENDENT_REVIEW", ["AGENT_REQUESTED_REVIEW_UNVERIFIED"]
    elif status == "COMPLETED" and task.task_type in ("review", "human_assessment"):
        kind, reasons = "REVIEW_OUTCOME_PENDING", ["REVIEW_NOT_INDEPENDENTLY_ATTESTED_NO_FURTHER_AGENT_REVIEW"]
    elif task.required_effects:
        # If the operation is still pending, verify existing H6/DEV scope
        # instead of implicitly demanding a fresh author decision.
        kind, reasons = "VERIFY_EXISTING_SCOPE", ["ORIGINAL_SCOPE_NOT_YET_VERIFIED"]
    elif status == "COMPLETED":
        refs = normalized.get("deliverables", {})
        if not isinstance(refs, dict):
            raise ValueError("INVALID_NORMALIZED_DELIVERABLES")
        if not sum(len(v) for v in refs.values()):
            kind, reasons = "RECONCILE", ["ARTIFACT_REFS_MISSING"]
        else:
            kind, reasons = "INDEPENDENT_REVIEW", ["AGENT_RESULT_REQUIRES_INDEPENDENT_REVIEW"]
    else:
        kind, reasons = "RECONCILE", ["RESULT_NOT_ACCEPTED"]

    # Next-role routing, not re-use of the old task's declared capability.
    from .next_task import _OBJECTIVES
    next_type, capability, _ = _OBJECTIVES[kind]
    if kind == "SWITCH_AGENT":
        # A replacement provider needs the previous task's actual skill, not
        # a generic review capability.
        capability = task.capability or task.task_type
    ready, unavailable = _real_candidates(
        capability, agents, normalized.get("agent_id")
        if kind in ("SWITCH_AGENT", "INDEPENDENT_REVIEW") else None)
    selected = ready[0] if ready else None
    if selected is None:
        reasons.append("NO_VERIFIED_REAL_AGENT_FOR_ROLE")
    decision = {
        "schema_version": "1.1",
        "project_id": task.project_id, "from_task_id": task.task_id,
        "decision_type": kind, "reason_codes": reasons,
        "authorization_status": auth_status,
        "suggested_capability": capability,
        "recommended_agent_id": selected,
        "declared_but_unavailable_agent_ids": unavailable[:8],
        "agent_selection_status": "VERIFIED_REAL_AGENT" if selected else "NOT_CONNECTED",
        "source_claim_trusted": False, "independent_review_completed": False,
        "execution_authorized": False, "can_auto_dispatch": False,
        "author_decision_required_for_effects": False,
        "next": "CHATGPT_REVIEW_CANDIDATE_WITH_ORIGINAL_PROJECT_EVIDENCE",
    }
    decision["next_task"] = propose_next_task(task, normalized, decision)
    return decision
