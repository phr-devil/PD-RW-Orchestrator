"""Deterministic candidate next actions; never scientific or permission attestation."""
from __future__ import annotations

from typing import Any

from .models import TaskPacket
from .policy import GuidancePacket
from .registry import AgentSpec

DECISION_TYPES = frozenset({
    "CONTINUE_SAME_AGENT", "SWITCH_AGENT", "INDEPENDENT_REVIEW",
    "REVISE_PLAN", "REQUEST_AUTHOR_DECISION", "RECONCILE", "HOLD",
    "READY_FOR_NEXT_STAGE",
})


def _real_candidates(capability: str, agents: tuple[AgentSpec, ...]) -> tuple[list[str], list[str]]:
    """Only a real provider whose host-backed readiness was proven may be selected.

    At v0.1 mock adapters are *never* considered real research executors.
    """
    relevant = sorted((a for a in agents if capability in a.capabilities),
                      key=lambda a: (a.priority, a.id))
    ready = [a.id for a in relevant if a.verified_ready and a.adapter != "mock"]
    unavailable = [a.id for a in relevant if a.id not in ready]
    return ready, unavailable


def decide_next(
    task: TaskPacket,
    normalized: dict[str, Any],
    guidance: GuidancePacket,
    agents: tuple[AgentSpec, ...],
    *,
    source_context: dict | None = None,
) -> dict:
    """Select a *draft* next action. All caller-supplied assertions are untrusted.

    source_context may only add blockers, never grant authorization or scientific
    credibility. Independent science review must eventually come from a trusted
    PD-RW-Agent/host bridge, not an Agent's JSON status or vote.
    """
    if normalized.get("project_id") != task.project_id or normalized.get("task_id") != task.task_id:
        raise ValueError("DECISION_TASK_IDENTITY_MISMATCH")
    if normalized.get("schema_version") != "2.0" or normalized.get("origin") != "UNTRUSTED_AGENT_OUTPUT":
        raise ValueError("UNVERIFIED_NORMALIZED_RESULT_REQUIRED")
    execution = normalized.get("execution", {})
    status = execution.get("reported_status")
    if not isinstance(status, str):
        raise ValueError("INVALID_NORMALIZED_RESULT")
    why: list[str] = []
    kind: str
    capability: str

    if source_context is not None:
        if not isinstance(source_context, dict):
            raise ValueError("INVALID_SOURCE_CONTEXT")
        if source_context.get("project_id") != task.project_id:
            kind, capability, why = "RECONCILE", "review", ["SOURCE_PROJECT_ID_MISMATCH"]
        elif (source_context.get("bridge_status") != "SOURCE_REVIEW_ONLY" or
              source_context.get("source_status") != "SOURCE_REVIEW_REQUIRED" or
              source_context.get("operational_reconciliation_required") or
              source_context.get("unresolved_operation_count", 0)):
            kind, capability, why = "RECONCILE", "review", ["SOURCE_RECONCILIATION_REQUIRED"]
        else:
            kind, capability = "", ""
    else:
        kind, capability = "", ""

    if not kind:
        if guidance.denied_effects:
            kind, capability, why = "HOLD", "review", ["POLICY_EFFECT_DENIED"]
        elif task.required_effects:
            kind, capability, why = "REQUEST_AUTHOR_DECISION", "review", ["TRUSTED_HOST_AUTH_NOT_CONNECTED"]
        elif status == "DEMO_ONLY":
            kind, capability, why = "RECONCILE", "review", ["MOCK_RESULT_NO_SCIENCE"]
        elif status == "BLOCKED_DEPENDENCY":
            kind, capability, why = "RECONCILE", "review", ["DEPENDENCY_NOT_RESOLVED"]
        elif status in ("BLOCKED_AUTH", "BLOCKED_POLICY"):
            kind, capability, why = ("REQUEST_AUTHOR_DECISION" if status == "BLOCKED_AUTH" else "HOLD"), "review", [status]
        elif status == "NOT_CONNECTED":
            kind, capability, why = "SWITCH_AGENT", task.capability or task.task_type, ["PREVIOUS_AGENT_NOT_CONNECTED"]
        elif status == "FAILED":
            kind, capability, why = "REVISE_PLAN", task.capability or task.task_type, ["EXECUTION_FAILED_CAUSE_UNVERIFIED"]
        elif status == "COMPLETED":
            count = sum(len(x) for x in normalized.get("deliverables", {}).values())
            if not count:
                kind, capability, why = "RECONCILE", "review", ["ARTIFACT_REFS_MISSING"]
            else:
                kind, capability, why = "INDEPENDENT_REVIEW", "review", ["AGENT_RESULT_REQUIRES_INDEPENDENT_REVIEW"]
        else:
            kind, capability, why = "RECONCILE", "review", ["RESULT_NOT_ACCEPTED"]

    if normalized.get("scientific_assessment", {}).get("effective_claim_status") != "NOT_ASSESSED":
        raise ValueError("UNEXPECTED_TRUST_ESCALATION")
    ready, unavailable = _real_candidates(capability, agents)
    selected = ready[0] if ready else None
    if not selected:
        why.append("NO_VERIFIED_REAL_AGENT_FOR_ROLE")
    return {
        "schema_version": "1.0",
        "project_id": task.project_id,
        "from_task_id": task.task_id,
        "decision_type": kind,
        "reason_codes": why,
        "suggested_capability": capability,
        "recommended_agent_id": selected,
        "declared_but_unavailable_agent_ids": unavailable[:8],
        "agent_selection_status": "VERIFIED_REAL_AGENT" if selected else "NOT_CONNECTED",
        "source_claim_trusted": False,
        "independent_review_completed": False,
        "execution_authorized": False,
        "can_auto_dispatch": False,
        "author_decision_required_for_effects": bool(task.required_effects),
        "next": "CHATGPT_REVIEW_CANDIDATE_WITH_ORIGINAL_PROJECT_EVIDENCE",
    }
