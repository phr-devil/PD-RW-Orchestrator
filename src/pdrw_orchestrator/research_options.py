"""Compare declared research options; no authority or scientific verdict."""
from __future__ import annotations

from .experience_evaluation import digest, _check, _text, _refs
from .registry import AgentSpec

_RESEARCH_ACTIONS = {"INDEPENDENT_REVIEW", "REVISE_PLAN", "REVIEW_OUTCOME_PENDING"}
_ROUTES = ("REUSE_EVIDENCE", "MINIMAL_CHECK", "REPAIR_METHOD", "CONTINUE_DEV",
           "NARROW_CLAIM", "PIVOT", "HOLD")
_METRICS = ("decision_value", "contribution_potential", "tokens", "wall_seconds")


def _integer(value, minimum=0, maximum=10**9):
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError("OPTION_NUMBER_INVALID")
    return value


def _dominates(a, b):
    # Never trade a lower decision value against publication potential or cost
    # by inventing a common utility scale.
    aa = (a["decision_value"], a["contribution_potential"], -a["tokens"], -a["wall_seconds"])
    bb = (b["decision_value"], b["contribution_potential"], -b["tokens"], -b["wall_seconds"])
    return all(x >= y for x,y in zip(aa,bb)) and any(x > y for x,y in zip(aa,bb))


def compare_options(bundle: dict, manifest: dict, agents: tuple[AgentSpec, ...]) -> dict:
    """Use an exact prior advisory context and bounded operator declarations.

    A frontier is not a recommended executable plan. Unknown prerequisites and
    new author decisions stay visible, rather than receiving invented scores.
    """
    _check(manifest, "schema_version project_id proposal_id context_sha256 remaining_budget options")
    if manifest["schema_version"] != "1.0" or bundle.get("mode") != "ADVISORY_DRAFT_ONLY":
        raise ValueError("OPTIONS_CONTRACT_INVALID")
    proposal = bundle["next_task"]
    if (manifest["project_id"] != bundle["project_id"] or
            manifest["proposal_id"] != proposal["proposal_id"] or
            manifest["context_sha256"] != context_digest(bundle)):
        raise ValueError("OPTIONS_CONTEXT_MISMATCH")
    budget = manifest["remaining_budget"]
    _check(budget, "tokens wall_seconds")
    for value in budget.values():
        if value is not None:
            _integer(value)
    options = manifest["options"]
    if not isinstance(options,list) or not 1 <= len(options) <= 12:
        raise ValueError("OPTIONS_COUNT_INVALID")
    seen, rows, eligible = set(), [], []
    decision = bundle["decision"]
    blocked = (decision["decision_type"] not in _RESEARCH_ACTIONS
               or decision.get("authorization_status") == "DENIED"
               or bool((bundle.get("source_context") or {}).get("operational_reconciliation_required"))
               or bool((bundle.get("source_context") or {}).get("unresolved_operation_count")))
    science = bundle["result"]["scientific_assessment"]
    invalid_report = (science.get("reported_protocol_status") == "INVALID"
                      or science.get("reported_outcome") == "INVALID")
    for option in options:
        _check(option, "id route premise evidence_refs discriminating_outcomes stop_rule capability prerequisite scope decision_value contribution_potential tokens wall_seconds")
        ident = _text(option["id"], 80)
        if ident in seen:
            raise ValueError("OPTION_DUPLICATE_ID")
        seen.add(ident)
        route = option["route"]
        if route not in _ROUTES:
            raise ValueError("OPTION_ROUTE_INVALID")
        for field in ("premise","stop_rule","capability"):
            _text(option[field])
        _refs(option["evidence_refs"])
        outcomes = option["discriminating_outcomes"]
        if not isinstance(outcomes,list) or not 2 <= len(outcomes) <= 4:
            raise ValueError("OPTION_DISCRIMINATING_OUTCOMES_REQUIRED")
        for outcome in outcomes:
            _text(outcome)
        if len(set(outcomes)) != len(outcomes):
            raise ValueError("OPTION_OUTCOMES_NOT_DISTINCT")
        if option["prerequisite"] not in ("SUPPORTED","UNKNOWN","CONTRADICTED"):
            raise ValueError("OPTION_PREREQUISITE_INVALID")
        if option["scope"] not in ("EXISTING_SCOPE_DECLARED","UNKNOWN","NEW_SCOPE"):
            raise ValueError("OPTION_SCOPE_INVALID")
        for key in _METRICS:
            if option[key] is not None:
                _integer(option[key], maximum=3 if key in _METRICS[:2] else 10**9)
        reasons = []
        if blocked:
            reasons.append("ORIGINAL_DECISION_BLOCKS_ROUTE_COMPARISON")
        if route in ("NARROW_CLAIM","PIVOT") or option["scope"] == "NEW_SCOPE":
            reasons.append("MATERIAL_CHANGE_REQUIRES_ORIGINAL_SCOPE_REVIEW")
        if option["scope"] == "UNKNOWN":
            reasons.append("EXISTING_SCOPE_UNVERIFIED")
        if option["prerequisite"] != "SUPPORTED":
            reasons.append("PREMISE_" + option["prerequisite"])
        if invalid_report and route == "CONTINUE_DEV":
            reasons.append("REPORTED_METHOD_INVALIDITY_REVIEW_FIRST")
        if any(option[k] is None for k in _METRICS) or any(v is None for v in budget.values()):
            reasons.append("RESOURCE_OR_VALUE_UNKNOWN")
        if any(option[k] is not None and budget[k] is not None and option[k] > budget[k] for k in budget):
            reasons.append("DECLARED_BUDGET_EXCEEDED")
        candidates = []
        for agent in sorted(agents,key=lambda a:(a.priority,a.id)):
            if agent.adapter == "mock" or option["capability"] not in agent.capabilities:
                continue
            if option["capability"] == "review" and agent.id == bundle["result"]["agent_id"]:
                continue
            candidates.append({"agent_id":agent.id,"capability_declared":True,
                               "host_ready_verified":agent.verified_ready})
        row = {**option,"comparison_blockers":reasons,
               "declared_agent_candidates":candidates[:8],
               "scientific_validity_verified":False,"execution_authorized":False}
        rows.append(row)
        if not reasons:
            eligible.append(row)
    frontier = [r["id"] for r in eligible if not any(_dominates(other,r) for other in eligible if other is not r)]
    return {"status": "ROUTE_FRONTIER_DECLARED_ONLY" if frontier else "NO_COMPARABLE_ROUTE",
            "project_id":manifest["project_id"],"proposal_id":manifest["proposal_id"],
            "context_sha256":manifest["context_sha256"],"manifest_sha256":digest(manifest),
            "frontier_option_ids":frontier,"options":rows,
            "selected_option_id":None,"recommended_agent_id":None,
            "original_decision_preserved":True,"authorization_verified":False,
            "execution_authorized":False,"scientific_validity_verified":False,
            "cost_measurement_verified":False,"model_calls_requested":0}


def context_digest(bundle):
    """Hash stable decision inputs, excluding derived output paths/route options."""
    return digest({key:bundle[key] for key in (
        "project_id","task_id","result","decision","next_guidance","source_context")})
