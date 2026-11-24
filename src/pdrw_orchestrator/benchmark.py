"""Offline historical replay and matched provider assessment, not dispatch."""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from . import __version__
from .agent_result import normalize_result
from .decision import DECISION_TYPES, decide_next
from .experience_evaluation import digest, _check, _text, _refs
from .models import TaskPacket
from .policy import compile_guidance


def _timestamp(value):
    if not isinstance(value, str) or len(value) > 40:
        raise ValueError("BENCHMARK_TIMESTAMP_INVALID")
    t = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if t.utcoffset() is None:
        raise ValueError("BENCHMARK_TIMESTAMP_NEEDS_OFFSET")
    return t


def _sha(value):
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise ValueError("BENCHMARK_HASH_INVALID")


def _rows(rows):
    if not isinstance(rows, list) or not 1 <= len(rows) <= 100:
        raise ValueError("BENCHMARK_COHORT_INVALID")
    ids = [_text(row["case_id"], 120) for row in rows]
    if len(set(ids)) != len(ids):
        raise ValueError("BENCHMARK_DUPLICATE_CASE")
    return ids


def replay(manifest, rules, agents):
    """Replay current engine on explicitly time-bounded declared historical inputs.

    References and availability times are declarations; no original project,
    provider, Experience catalog or current live source is consulted.
    """
    _check(manifest, "schema_version cases reference_commitment_sha256")
    commitment = manifest["reference_commitment_sha256"]
    if commitment is not None:
        _sha(commitment)
    if manifest["schema_version"] != "1.0":
        raise ValueError("BENCHMARK_VERSION_INVALID")
    _rows(manifest["cases"])
    output = []
    for case in manifest["cases"]:
        _check(case, "case_id cutoff input_status availability_refs inputs")
        cutoff = _timestamp(case["cutoff"])
        _refs(case["availability_refs"])
        base = {"case_id":case["case_id"], "case_sha256":digest(case), "cutoff":case["cutoff"]}
        if case["input_status"] == "UNAVAILABLE":
            if case["inputs"] is not None:
                raise ValueError("BENCHMARK_UNAVAILABLE_INPUT_CONFLICT")
            output.append({**base, "status":"INPUT_UNAVAILABLE", "decision_type":None})
            continue
        if case["input_status"] != "AVAILABLE":
            raise ValueError("BENCHMARK_INPUT_STATUS_INVALID")
        inputs = case["inputs"]
        _check(inputs, "task result source_context available_at")
        _check(inputs["available_at"], "task result source_context")
        for name in ("task","result","source_context"):
            value = inputs[name]
            when = inputs["available_at"][name]
            if name == "source_context" and value is None:
                if when is not None:
                    raise ValueError("BENCHMARK_NULL_SOURCE_DATE_CONFLICT")
            elif _timestamp(when) > cutoff:
                raise ValueError("BENCHMARK_FUTURE_INPUT")
        try:
            task = TaskPacket(**inputs["task"])
            result = normalize_result(inputs["result"], task)
            decision = decide_next(task, result, compile_guidance(task, rules), agents,
                                   source_context=inputs["source_context"])
        except (ValueError, TypeError, KeyError):
            output.append({**base, "status":"INPUT_REJECTED", "decision_type":None})
            continue
        output.append({**base, "status":"REPLAYED", "decision_type":decision["decision_type"],
                       "reason_codes":decision["reason_codes"],
                       "execution_authorized":False})
    return {"status":"HISTORICAL_REPLAY_DECLARED_INPUTS_ONLY",
            "engine_version":__version__, "manifest_sha256":digest(manifest),
            "reference_commitment_sha256":commitment,
            "policy_sha256":digest([asdict(r) for r in rules]),
            "registry_sha256":digest([asdict(a) for a in agents]),
            "cases":output, "historical_availability_verified":False,
            "future_information_absence_verified":False, "model_calls_requested":0,
            "execution_authorized":False}


def assess(replayed, reference):
    """Join a separate reference assessment to the exact replay, never to inputs."""
    _check(reference, "schema_version replay_sha256 cases")
    if (reference["schema_version"] != "1.0" or
            replayed.get("status") != "HISTORICAL_REPLAY_DECLARED_INPUTS_ONLY" or
            reference["replay_sha256"] != digest(replayed)):
        raise ValueError("BENCHMARK_REPLAY_BINDING_MISMATCH")
    actual = replayed["cases"]
    expected = reference["cases"]
    commitment = replayed.get("reference_commitment_sha256")
    if commitment is not None and commitment != digest(expected):
        raise ValueError("BENCHMARK_REFERENCE_COMMITMENT_MISMATCH")
    if set(_rows(actual)) != set(_rows(expected)):
        raise ValueError("BENCHMARK_COHORT_MISMATCH")
    by_id = {r["case_id"]:r for r in expected}
    rows = []
    for item in actual:
        ref = by_id[item["case_id"]]
        _check(ref, "case_id case_sha256 reference_status acceptable_decisions evidence_refs")
        if ref["case_sha256"] != item["case_sha256"]:
            raise ValueError("BENCHMARK_CASE_BINDING_MISMATCH")
        _refs(ref["evidence_refs"])
        choices = ref["acceptable_decisions"]
        if ref["reference_status"] == "UNKNOWN":
            if choices != []:
                raise ValueError("BENCHMARK_UNKNOWN_REFERENCE_CONFLICT")
        elif (ref["reference_status"] != "REVIEWED_DECLARED" or not isinstance(choices,list)
                or not choices or len(choices)>len(DECISION_TYPES)
                or any(not isinstance(c,str) or c not in DECISION_TYPES for c in choices)):
            raise ValueError("BENCHMARK_REFERENCE_INVALID")
        if item["status"] not in ("REPLAYED","INPUT_UNAVAILABLE","INPUT_REJECTED") or (
                item["status"] == "REPLAYED" and item["decision_type"] not in DECISION_TYPES):
            raise ValueError("BENCHMARK_REPLAY_ROW_INVALID")
        if item["status"] != "REPLAYED":
            status = item["status"]
        elif ref["reference_status"] == "UNKNOWN":
            status = "REFERENCE_UNKNOWN"
        else:
            status = "MATCH" if item["decision_type"] in choices else "MISMATCH"
        rows.append({"case_id":item["case_id"],"status":status,
                     "decision_type":item["decision_type"],"acceptable_decisions":choices})
    matches = sum(r["status"]=="MATCH" for r in rows)
    assessed = matches + sum(r["status"]=="MISMATCH" for r in rows)
    return {"status":"DESCRIPTIVE_HISTORICAL_ASSESSMENT_ONLY","cohort_count":len(rows),
            "assessed_count":assessed,"match_count":matches,
            "match_rate_assessed":matches/assessed if assessed else None,
            "match_fraction_full_cohort":matches/len(rows),"cases":rows,
            "replay_sha256":digest(replayed),"reference_sha256":digest(reference),
            "reference_commitment_matched": commitment is not None,
            "reference_commitment_time_verified":False,
            "reference_independence_verified":False,"scientific_efficacy_verified":False,
            "execution_authorized":False}


_RUBRIC = ("source_legality","scientific_validity","decision_relevance","avoids_redundant_work")


def compare_providers(manifest, agents):
    """Compare two versioned providers on a declared identical case cohort.

    No general readiness, automatic priority change or statistical claim.
    """
    _check(manifest, "schema_version capability providers cases")
    if manifest["schema_version"] != "1.0":
        raise ValueError("BENCHMARK_VERSION_INVALID")
    capability = _text(manifest["capability"],80)
    providers = manifest["providers"]
    if not isinstance(providers,list) or len(providers)!=2:
        raise ValueError("BENCHMARK_TWO_PROVIDERS_REQUIRED")
    declared = {a.id:a for a in agents if a.adapter!="mock" and capability in a.capabilities}
    for p in providers:
        _check(p,"agent_id version config_sha256")
        _text(p["version"],160)
        _sha(p["config_sha256"])
        if p["agent_id"] not in declared:
            raise ValueError("BENCHMARK_CAPABILITY_NOT_DECLARED")
    ids = [p["agent_id"] for p in providers]
    if ids[0]==ids[1]:
        raise ValueError("BENCHMARK_DISTINCT_PROVIDERS_REQUIRED")
    _rows(manifest["cases"])
    rows, used_refs = [], set()
    for case in manifest["cases"]:
        _check(case,"case_id protocol_sha256 budget arms")
        _sha(case["protocol_sha256"])
        budget = case["budget"]
        _check(budget,"tokens wall_seconds")
        if any(type(v) is not int or v<=0 for v in budget.values()):
            raise ValueError("BENCHMARK_BUDGET_INVALID")
        arms = case["arms"]
        if not isinstance(arms,list) or len(arms)!=2:
            raise ValueError("BENCHMARK_PAIR_INCOMPLETE")
        for index, arm in enumerate(arms):
            _check(arm,"agent_id provider_sha256 protocol_sha256 status result_ref reviewer_ref rubric tokens wall_seconds")
            if (arm["agent_id"]!=ids[index] or arm["provider_sha256"]!=digest(providers[index])
                    or arm["protocol_sha256"]!=case["protocol_sha256"]):
                raise ValueError("BENCHMARK_PAIR_BINDING_MISMATCH")
            if arm["status"] not in ("COMPLETED","FAILED","UNKNOWN","NOT_RUN"):
                raise ValueError("BENCHMARK_ARM_STATUS_INVALID")
            if arm["status"] in ("COMPLETED","FAILED"):
                ref = _text(arm["result_ref"])
                if ref in used_refs:
                    raise ValueError("BENCHMARK_RESULT_REF_REUSED")
                used_refs.add(ref)
            elif arm["result_ref"] is not None:
                if arm["status"] == "NOT_RUN":
                    raise ValueError("BENCHMARK_NOT_RUN_RESULT_CONFLICT")
                ref = _text(arm["result_ref"])
                if ref in used_refs:
                    raise ValueError("BENCHMARK_RESULT_REF_REUSED")
                used_refs.add(ref)
            for key in budget:
                value = arm[key]
                if value is not None and (type(value) is not int or value<0):
                    raise ValueError("BENCHMARK_COST_INVALID")
                if arm["status"]=="NOT_RUN" and value is not None:
                    raise ValueError("BENCHMARK_NOT_RUN_COST_CONFLICT")
            if arm["rubric"] is not None:
                if arm["status"]!="COMPLETED":
                    raise ValueError("BENCHMARK_UNCOMPLETED_RUBRIC")
                _text(arm["reviewer_ref"])
                _check(arm["rubric"]," ".join(_RUBRIC))
                if any(type(v) is not int or v not in (0,1) for v in arm["rubric"].values()):
                    raise ValueError("BENCHMARK_RUBRIC_INVALID")
            elif arm["reviewer_ref"] is not None:
                _text(arm["reviewer_ref"])
        a,b = arms
        over = [arm["agent_id"] for arm in arms if any(
            arm[k] is not None and arm[k]>budget[k] for k in budget)]
        unknown_budget = [arm["agent_id"] for arm in arms if any(arm[k] is None for k in budget)]
        delta = None
        if not over and a["rubric"] is not None and b["rubric"] is not None:
            delta = {k:b["rubric"][k]-a["rubric"][k] for k in _RUBRIC}
        rows.append({"case_id":case["case_id"],"statuses":[a["status"],b["status"]],
                     "budget_exceeded_declared":over,"budget_unknown":unknown_budget,
                     "within_budget_declared":not over and not unknown_budget,"rubric_delta":delta,
                     "critical_regression": (any(delta[k]<0 for k in _RUBRIC[:2]) if delta is not None else None),
                     **{k+"_delta":b[k]-a[k] if None not in (a[k],b[k]) else None for k in budget}})
    return {"status":"MATCHED_PROVIDER_DESCRIPTIVE_ONLY","provider_ids":ids,
            "capability":capability,"cohort_count":len(rows),
            paired_rubric_count":sum(r["rubric_delta"] is not None for r in rows),
            "within_budget_paired_rubric_count":sum(r["rubric_delta"] is not None and r["within_budget_declared"] for r in rows),
            "critical_regression_count":sum(r["critical_regression"] is True for r in rows),
            "completion_counts":{ident:sum(r["statuses"][i]=="COMPLETED" for r in rows) for i,ident in enumerate(ids)},
            "pairs":rows,"manifest_sha256":digest(manifest),
            "matched_protocol_verified":False,"actual_usage_verified":False,
            "provider_readiness_verified":False,"routing_priority_changed":False,
            "scientific_efficacy_verified":False,"execution_authorized":False}
