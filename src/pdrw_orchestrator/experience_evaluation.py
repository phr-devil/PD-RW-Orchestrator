"""M3-B: conditional advisory screening and offline evidence-linked evaluation.

All assessments are operator-supplied declarations, not independently verified
science. No execution, lesson mutation or automatic promotion is performed.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import date
from statistics import mean


def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False,
        separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def _check(obj, fields):
    if not isinstance(obj, dict) or set(obj) != set(fields.split()):
        raise ValueError("INVALID_EVALUATION_FIELDS")


def _text(value, limit=500):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError("INVALID_EVALUATION_TEXT")
    return value


def _refs(value):
    if not isinstance(value, list) or not 1 <= len(value) <= 8:
        raise ValueError("INVALID_EVALUATION_EVIDENCE")
    for ref in value:
        _text(ref)
    return value


def screen_lessons(task, rules, context=None):
    """Keep unknown conditions as review hypotheses; exclude declared mismatches.

    Bind condition judgments to the exact rule bytes and proposed task. Stale
    judgments do not transfer to changed lessons or a different project.
    """
    rows = {}
    if context is not None:
        _check(context, "schema_version project_id task_id assessments")
        if (context["schema_version"] != "1.0" or context["project_id"] != task.project_id
                or context["task_id"] != task.task_id):
            raise ValueError("APPLICABILITY_TASK_MISMATCH")
        entries = context["assessments"]
        if not isinstance(entries, list) or len(entries) > 12:
            raise ValueError("APPLICABILITY_COUNT_INVALID")
        for row in entries:
            _check(row, "rule_id rule_sha256 conditions")
            ident = _text(row["rule_id"], 160)
            _text(row["rule_sha256"], 64)
            if ident in rows or not isinstance(row["conditions"], list) or len(row["conditions"]) > 8:
                raise ValueError("APPLICABILITY_DUPLICATE_OR_INVALID")
            judgments = {}
            for condition in row["conditions"]:
                _check(condition, "condition status evidence_refs")
                key = _text(condition["condition"])
                if key in judgments or condition["status"] not in ("MATCH", "MISMATCH", "UNKNOWN"):
                    raise ValueError("APPLICABILITY_CONDITION_INVALID")
                if condition["status"] != "UNKNOWN":
                    _refs(condition["evidence_refs"])
                elif condition["evidence_refs"] != []:
                    _refs(condition["evidence_refs"])
                judgments[key] = condition
            rows[ident] = (row["rule_sha256"], judgments)
    retained, audit = [], []
    for rule in rules:
        fingerprint = digest(asdict(rule))
        row = rows.get(rule.id)
        valid = row is not None and row[0] == fingerprint and set(row[1]) == set(rule.conditions)
        conditions = [row[1][c] for c in rule.conditions] if valid else []
        statuses = [x["status"] for x in conditions]
        if "MISMATCH" in statuses:
            status = "EXCLUDED_DECLARED_MISMATCH"
        elif rule.conditions and valid and all(x == "MATCH" for x in statuses):
            status = "DECLARED_MATCH_UNVERIFIED"
        else:
            status = "REVIEW_ONLY_APPLICABILITY_UNKNOWN"
        if status != "EXCLUDED_DECLARED_MISMATCH":
            retained.append(rule)
        audit.append({"rule_id": rule.id, "rule_sha256": fingerprint,
                      "status": status, "conditions": list(rule.conditions),
                      "declared_condition_evidence": conditions,
                      "applicability_verified": False, "stale_or_incomplete": row is not None and not valid})
    return tuple(retained), audit


def feedback_candidate(bundle, assessment):
    """Build a candidate in upstream feedback v1 shape, with separate channels.

    The selected lesson and proposal are bound to the supplied handoff bytes.
    This does not prove the task actually ran or the reviewer is authentic.
    """
    _check(assessment, "schema_version project_id task_id rule_id rule_sha256 observed_at science engineering transfer usage observation evidence_refs")
    if assessment["schema_version"] != "1.0" or bundle.get("mode") != "ADVISORY_DRAFT_ONLY":
        raise ValueError("FEEDBACK_CONTRACT_INVALID")
    proposal = bundle["next_task"]
    if (assessment["project_id"] != bundle["project_id"] or
            assessment["task_id"] != proposal["proposal_id"]):
        raise ValueError("FEEDBACK_TASK_MISMATCH")
    retrieval = bundle.get("experience_retrieval", {})
    ident = assessment["rule_id"]
    selected = retrieval.get("selected_experience_rule_ids", [])
    records = [x for x in retrieval.get("applicability_screen", [])
               if x["rule_id"] == ident and x["rule_sha256"] == assessment["rule_sha256"]]
    if ident not in selected or len(records) != 1 or records[0]["status"] == "EXCLUDED_DECLARED_MISMATCH":
        raise ValueError("FEEDBACK_LESSON_NOT_SELECTED_OR_VERSION_MISMATCH")
    if not any(x["id"] == ident and x["level"] == "experience"
               for x in bundle["next_guidance"]["selected_items"]):
        raise ValueError("FEEDBACK_LESSON_NOT_IN_GUIDANCE")
    observed = assessment["observed_at"]
    if date.fromisoformat(observed).isoformat() != observed:
        raise ValueError("FEEDBACK_DATE_INVALID")
    if retrieval.get("as_of") and observed < retrieval["as_of"]:
        raise ValueError("FEEDBACK_PRECEDES_VISIBILITY")
    science = assessment["science"]
    engineering = assessment["engineering"]
    transfer = assessment["transfer"]
    usage = assessment["usage"]
    if usage not in ("APPLIED", "NOT_APPLIED", "UNKNOWN"):
        raise ValueError("FEEDBACK_USAGE_INVALID")
    if science not in ("POSITIVE", "NEGATIVE", "MIXED", "INCONCLUSIVE", "INVALID", "UNKNOWN"):
        raise ValueError("FEEDBACK_SCIENCE_INVALID")
    if engineering not in ("COMPLETED", "FAILED", "UNKNOWN") or transfer not in ("HELPFUL", "HARMFUL", "NO_EFFECT", "UNKNOWN"):
        raise ValueError("FEEDBACK_CHANNEL_INVALID")
    # An experiment's negative result is not evidence that the lesson harmed it.
    # Require a separate explicit transfer assessment; unresolved engineering
    # and invalid/unknown science cannot support a directional feedback outcome.
    outcome = "INCONCLUSIVE"
    if usage == "APPLIED" and engineering == "COMPLETED" and science not in ("INVALID", "UNKNOWN", "INCONCLUSIVE"):
        outcome = {"HELPFUL": "POSITIVE", "HARMFUL": "NEGATIVE"}.get(transfer, "INCONCLUSIVE")
    lesson_id, marker, version = ident.rpartition(":v")
    if not marker or not lesson_id or not version.isdecimal():
        raise ValueError("FEEDBACK_VERSIONED_LESSON_ID_REQUIRED")
    refs = _refs(assessment["evidence_refs"])
    observation = _text(assessment["observation"], 1200)
    candidate = {"schema_version": "1.0", "task_id": assessment["task_id"],
        "lesson_id": lesson_id, "observed_at": observed, "outcome": outcome,
        "observation": f"Unverified assessment of {ident}; science={science}; engineering={engineering}; usage={usage}; transfer={transfer}. {observation}",
        "evidence_refs": refs}
    return {"status": "FEEDBACK_CANDIDATE_UNVERIFIED", "feedback": candidate,
        "rule_id": ident, "rule_sha256": assessment["rule_sha256"],
        "handoff_sha256": digest(bundle), "science": science, "engineering": engineering,
        "transfer": transfer, "usage_declared": usage, "actual_usage_verified": False,
        "negative_transfer_candidate": outcome == "NEGATIVE",
        "scientific_validity_verified": False, "automatic_lesson_update": False,
        "automatic_rule_promotion": False, "permission_granted": False}


_RUBRIC = ("source_legality", "scientific_validity", "decision_relevance", "avoids_redundant_work")


def evaluate_pairs(manifest):
    """Descriptive matched-pair audit, not causal or statistically powered evidence."""
    _check(manifest, "schema_version pairs")
    pairs = manifest["pairs"]
    if manifest["schema_version"] != "1.0" or not isinstance(pairs, list) or not 1 <= len(pairs) <= 100:
        raise ValueError("PAIR_MANIFEST_INVALID")
    seen, rows = set(), []
    for pair in pairs:
        _check(pair, "case_id protocol_sha256 without_experience with_experience")
        ident = _text(pair["case_id"], 160)
        if ident in seen:
            raise ValueError("PAIR_DUPLICATE_CASE")
        seen.add(ident)
        protocol = _text(pair["protocol_sha256"], 64)
        if len(protocol) != 64 or any(c not in "0123456789abcdef" for c in protocol):
            raise ValueError("PAIR_PROTOCOL_HASH_INVALID")
        for arm in (pair["without_experience"], pair["with_experience"]):
            _check(arm, "protocol_sha256 result_ref reviewer_ref rubric tokens wall_seconds")
            if arm["protocol_sha256"] != protocol:
                raise ValueError("PAIR_PROTOCOL_MISMATCH")
            _text(arm["result_ref"])
            _text(arm["reviewer_ref"])
            _check(arm["rubric"], " ".join(_RUBRIC))
            if any(type(v) is not int or v not in (0, 1) for v in arm["rubric"].values()):
                raise ValueError("PAIR_RUBRIC_INVALID")
            for key in ("tokens", "wall_seconds"):
                if type(arm[key]) is not int or arm[key] < 0:
                    raise ValueError("PAIR_COST_INVALID")
        a,b = pair["without_experience"],pair["with_experience"]
        if a["result_ref"] == b["result_ref"]:
            raise ValueError("PAIR_IDENTICAL_RESULT_REF")
        delta = {k: b["rubric"][k]-a["rubric"][k] for k in _RUBRIC}
        critical_loss = any(delta[k] < 0 for k in ("source_legality", "scientific_validity"))
        rows.append({"case_id":ident, "rubric_delta":delta, "quality_delta":sum(delta.values()),
                     "critical_regression":critical_loss, "tokens_delta":b["tokens"]-a["tokens"],
                     "wall_seconds_delta":b["wall_seconds"]-a["wall_seconds"]})
    return {"status":"DESCRIPTIVE_PAIRED_EVALUATION_ONLY", "pair_count":len(rows),
            "critical_regression_count":sum(r["critical_regression"] for r in rows),
            "negative_transfer_candidates":sum(r["critical_regression"] or r["quality_delta"] < 0 for r in rows),
            "mean_quality_delta":mean(r["quality_delta"] for r in rows),
            "total_tokens_delta":sum(r["tokens_delta"] for r in rows),
            "total_wall_seconds_delta":sum(r["wall_seconds_delta"] for r in rows),
            "pairs":rows, "matched_protocol_declared_only":True,
            "independent_review_verified":False, "causal_effect_verified":False,
            "automatic_lesson_update":False, "permission_granted":False}
