"""Versioned agent self-report normalization; source claims are never attestations.

The existing models.ResultPacket v1 and all existing workflows remain unchanged.
This module accepts a bounded external report and exports v2 with explicit
reported vs effective evidence/claim statuses. No source assertion can certify
scientific truth, authorization, or successful execution.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .models import RESULT_STATUSES, ResultPacket, TaskPacket

_RESULT_VERSION = "2.0"
_REPORTED_CLAIMS = frozenset({"NOT_ASSESSED", "VALID", "INVALID", "UNCERTAIN"})
_REPORTED_PROTOCOLS = frozenset({"NOT_ASSESSED", "VALID", "INVALID", "UNCERTAIN"})
_REPORTED_OUTCOMES = frozenset({"NOT_ASSESSED", "POSITIVE", "NEGATIVE", "MIXED", "INCONCLUSIVE", "INVALID"})
_DELIVERABLE_FIELDS = ("code_refs", "run_refs", "evidence_refs", "report_refs")
_MAX_ITEMS = 32
_MAX_TEXT = 3000
_ROOT_FIELDS = frozenset({
    "schema_version", "project_id", "task_id", "agent_id", "attempt_id",
    "execution", "deliverables", "findings", "scientific_assessment",
    "unresolved_issues", "next_action_candidates",
    "authorization_verified", "scientific_completion_verified",
})


def _text(value: Any, label: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or len(value) > _MAX_TEXT or (
        not allow_empty and not value.strip()
    ):
        raise ValueError(f"INVALID_{label.upper()}")
    return value


def _strings(value: Any, label: str, *, maximum: int = _MAX_ITEMS) -> list[str]:
    if not isinstance(value, (list, tuple)) or len(value) > maximum:
        raise ValueError(f"INVALID_{label.upper()}")
    return [_text(item, label) for item in value]


def _findings(value: Any) -> list[dict]:
    if not isinstance(value, list) or len(value) > 16:
        raise ValueError("INVALID_FINDINGS")
    normalized = []
    for item in value:
        if not isinstance(item, dict) or set(item) - {
            "claim", "source_refs", "limitations",
        }:
            raise ValueError("INVALID_FINDING_FIELDS")
        normalized.append({
            "claim": _text(item.get("claim"), "finding_claim"),
            "source_refs": _strings(item.get("source_refs", []), "source_refs"),
            "limitations": _strings(item.get("limitations", []), "limitations"),
        })
    return normalized


def normalize_result(raw: Mapping[str, Any] | ResultPacket, task: TaskPacket) -> dict:
    """Normalize an untrusted v1/v2 report. Project/task mismatch fails closed."""
    if isinstance(raw, ResultPacket):
        raw = raw.to_dict()
    if not isinstance(raw, Mapping):
        raise ValueError("RESULT_OBJECT_REQUIRED")
    version = raw.get("schema_version")
    if version not in ("1.0", "2.0"):
        raise ValueError("UNSUPPORTED_RESULT_VERSION")
    if raw.get("task_id") != task.task_id:
        raise ValueError("RESULT_TASK_ID_MISMATCH")
    if version == "2.0" and raw.get("project_id") != task.project_id:
        raise ValueError("RESULT_PROJECT_ID_MISMATCH")
    agent_id = _text(raw.get("agent_id"), "agent_id")
    warnings = ["UNTRUSTED_AGENT_SELF_REPORT"]
    if version == "1.0":
        status = raw.get("status")
        refs = _strings(raw.get("output_refs", []), "output_refs")
        deliverables = dict.fromkeys(_DELIVERABLE_FIELDS)
        deliverables = {key: (refs if key == "report_refs" else [])
                        for key in _DELIVERABLE_FIELDS}
        findings = []
        issues = []
        candidates = []
        attempt_id = "UNSPECIFIED"
        budget_exhausted = False
        reported_claim = "NOT_ASSESSED"
        reported_protocol = "NOT_ASSESSED"
        reported_outcome = "NOT_ASSESSED"
        if raw.get("scientific_verified") is True:
            warnings.append("UNTRUSTED_SCIENCE_ATTESTATION_IGNORED")
    else:
        if set(raw) - _ROOT_FIELDS:
            raise ValueError("UNKNOWN_RESULT_FIELDS")
        attempt_id = _text(raw.get("attempt_id"), "attempt_id")
        execution = raw.get("execution")
        if not isinstance(execution, dict) or set(execution) - {
            "status", "budget_exhausted",
        }:
            raise ValueError("INVALID_EXECUTION")
        status = execution.get("status")
        budget_exhausted = execution.get("budget_exhausted", False)
        if type(budget_exhausted) is not bool:
            raise ValueError("INVALID_BUDGET_EXHAUSTED")
        raw_refs = raw.get("deliverables", {})
        if not isinstance(raw_refs, dict) or set(raw_refs) - set(_DELIVERABLE_FIELDS):
            raise ValueError("INVALID_DELIVERABLES")
        deliverables = {
            key: _strings(raw_refs.get(key, []), key) for key in _DELIVERABLE_FIELDS
        }
        findings = _findings(raw.get("findings", []))
        issues = _strings(raw.get("unresolved_issues", []), "unresolved_issues")
        candidates = _strings(raw.get("next_action_candidates", []),
                              "next_action_candidates", maximum=8)
        science = raw.get("scientific_assessment", {})
        if not isinstance(science, dict) or set(science) - {
            "claim_status", "protocol_status", "review_required", "outcome",
        }:
            raise ValueError("INVALID_SCIENTIFIC_ASSESSMENT")
        reported_claim = science.get("claim_status", "NOT_ASSESSED")
        reported_protocol = science.get("protocol_status", "NOT_ASSESSED")
        reported_outcome = science.get("outcome", "NOT_ASSESSED")
        if (not isinstance(reported_claim, str) or reported_claim not in _REPORTED_CLAIMS
                or not isinstance(reported_protocol, str) or reported_protocol not in _REPORTED_PROTOCOLS
                or not isinstance(reported_outcome, str) or reported_outcome not in _REPORTED_OUTCOMES):
            raise ValueError("INVALID_REPORTED_SCIENTIFIC_STATUS")
        if "review_required" in science and type(science["review_required"]) is not bool:
            raise ValueError("INVALID_REVIEW_REQUIRED")
        if (reported_claim != "NOT_ASSESSED" or reported_protocol != "NOT_ASSESSED"
                or science.get("review_required") is False):
            warnings.append("SELF_REPORTED_SCIENCE_NOT_ATTESTED")
    if not isinstance(status, str) or status not in RESULT_STATUSES:
        raise ValueError("INVALID_EXECUTION_STATUS")
    if (raw.get("authorization_verified") is True or
            raw.get("scientific_completion_verified") is True):
        warnings.append("SELF_ASSERTED_AUTH_OR_COMPLETION_IGNORED")
    refs_count = sum(len(item) for item in deliverables.values())
    if status == "COMPLETED" and not refs_count:
        warnings.append("COMPLETED_WITHOUT_ARTIFACT_REFS")
    if status == "DEMO_ONLY":
        warnings.append("MOCK_OUTPUT_NOT_SCIENTIFIC_EVIDENCE")
    return {
        "schema_version": _RESULT_VERSION,
        "project_id": task.project_id,
        "task_id": task.task_id,
        "agent_id": agent_id,
        "attempt_id": attempt_id,
        "origin": "UNTRUSTED_AGENT_OUTPUT",
        "execution": {
            "reported_status": status,
            "budget_exhausted": budget_exhausted,
            "completion_attested": False,
        },
        "deliverables": deliverables,
        "findings": findings,
        "scientific_assessment": {
            "reported_claim_status": reported_claim,
            "reported_protocol_status": reported_protocol,
            "reported_outcome": reported_outcome,
            "effective_claim_status": "NOT_ASSESSED",
            "effective_protocol_status": "NOT_ASSESSED",
            "evidence_status": "REFERENCES_UNVERIFIED" if refs_count else "NO_REFERENCES",
            "independent_review_required": True,
        },
        "unresolved_issues": issues,
        "next_action_candidates": candidates,
        "warning_codes": warnings,
        "authorization_verified": False,
        "scientific_completion_verified": False,
        "dispatch_performed": False,
    }
