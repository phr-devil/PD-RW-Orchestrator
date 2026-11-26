"""Opt-in public Crossref/Zenodo metadata through ToolUniverse native REST tools.

The optional dependency is installed by the operator in a dedicated environment.
No generated code, LLM, generic tool dispatch, arbitrary endpoint or auto install.
Source subset matching is not an environment/permission attestation.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
from pathlib import Path

from .. import aide_pilot
from ..models import TaskPacket
from ..policy import compile_guidance
from .aide_install import inspect_specialist_install

_REVISION = "23168a559128900f743be48f4094e4b99596f672"
_FIELDS = {"schema_version", "project_id", "task_id", "attempt_id", "operation", "public_text", "limit"}
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}\Z")
_DOI = re.compile(r"10\.[0-9]{4,9}/[^\s\x00-\x1f]{1,220}\Z", re.I)


def _digest(value):
    return hashlib.sha256(aide_pilot._canonical(value)).hexdigest()


def preview(plan, rules=()):
    if not isinstance(plan, dict) or set(plan) != _FIELDS or plan["schema_version"] not in ("tooluniverse-public-literature-v1", "tooluniverse-public-dataset-v1"):
        raise ValueError("TOOLUNIVERSE_PLAN_INVALID")
    if any(not isinstance(plan[k], str) or not _ID.fullmatch(plan[k])
           for k in ("project_id", "task_id", "attempt_id")):
        raise ValueError("TOOLUNIVERSE_ID_INVALID")
    text, op, limit = plan["public_text"], plan["operation"], plan["limit"]
    if not isinstance(text, str) or not text.strip() or len(text) > 500 or any(ord(c) < 32 for c in text):
        raise ValueError("TOOLUNIVERSE_PUBLIC_TEXT_INVALID")
    if (op == "dataset") != (plan["schema_version"] == "tooluniverse-public-dataset-v1"):
        raise ValueError("TOOLUNIVERSE_SCHEMA_OPERATION_MISMATCH")
    if op == "dataset" and type(limit) is int and 1 <= limit <= 20:
        call = {"name": "Zenodo_search_records", "arguments": {
            "query": "resource_type.type:dataset AND (" + text + ")", "limit": limit, "page": 1}}
    elif op == "search" and type(limit) is int and 1 <= limit <= 20:
        call = {"name": "Crossref_search_works", "arguments": {"query": text, "limit": limit}}
    elif op == "doi" and type(limit) is int and limit == 1 and _DOI.fullmatch(text):
        call = {"name": "Crossref_get_work", "arguments": {"doi": text}}
    else:
        raise ValueError("TOOLUNIVERSE_OPERATION_OR_LIMIT_INVALID")
    task = TaskPacket(project_id=plan["project_id"], task_id=plan["task_id"],
                      task_type="discovery", capability={"search": "literature_lookup", "doi": "doi_lookup", "dataset": "dataset_lookup"}[op],
                      objective="Retrieve public dataset metadata: " + text if op == "dataset" else "Retrieve public bibliographic metadata: " + text,
                      required_effects=("network",), budget={"max_attempts": 1, "max_model_calls": 0})
    guidance = compile_guidance(task, rules)
    return {"status": "PUBLIC_LOOKUP_PREVIEW_ONLY", "task": task.to_dict(),
            "upstream_revision": _REVISION, "plan_sha256": _digest(plan),
            "native_call": call, "guidance": guidance.to_dict(),
            "blocked_by_policy": bool(guidance.denied_effects),
            "network_requests_performed": False, "execution_authorized": False,
            "model_calls_requested": 0}


def _native_call(call, source_root):
    source = inspect_specialist_install("tooluniverse", source_root)
    if source["status"] != "PINNED_SELECTED_BYTES_MATCH":
        raise ValueError("TOOLUNIVERSE_PINNED_SOURCE_NOT_MATCHED")
    root = Path(source_root)
    expected = root / "tooluniverse" / "__init__.py"
    spec = importlib.util.find_spec("tooluniverse")
    if spec is None or spec.origin is None or Path(spec.origin).resolve() != expected.resolve():
        raise ValueError("TOOLUNIVERSE_ACTIVE_PACKAGE_MISMATCH")
    # Use the native tool class/config directly; do not load the entire catalog,
    # workspace profile, generic SDK dispatch, other tools, or any LLM.
    dataset = call["name"] == "Zenodo_search_records"
    config_name = "zenodo_tools.json" if dataset else "crossref_tools.json"
    configs = json.loads(aide_pilot._read(root / "tooluniverse" / "data" / config_name, 2*1024*1024))
    matches = [c for c in configs if c.get("name") == call["name"]]
    if len(matches) != 1:
        raise ValueError("TOOLUNIVERSE_NATIVE_CONFIG_MISMATCH")
    # Upstream's supported light-import mode avoids initializing unrelated SDK/MCP modules.
    # Intended for a fresh dedicated CLI process; it is not process isolation.
    os.environ.setdefault("TOOLUNIVERSE_LIGHT_IMPORT", "true")
    try:
        from tooluniverse import credential_context
        if dataset:
            from tooluniverse.zenodo_tool import ZenodoRESTTool as NativeTool
        else:
            from tooluniverse.crossref_tool import CrossrefRESTTool as NativeTool
        with credential_context({}):
            tool = NativeTool(matches[0])
            tool.timeout = 20
            # requests otherwise consults ambient proxies and .netrc credentials.
            # An approved direct connection is required; no implicit proxy fallback.
            tool.session.trust_env = False
            try:
                return tool.run(call["arguments"])
            finally:
                tool.session.close()
    except Exception as exc:
        # Do not echo upstream raw errors, credentials, or transport payloads.
        raise ValueError("TOOLUNIVERSE_NATIVE_CALL_FAILED") from None


def _text(value, maximum):
    if isinstance(value, list):
        value = next((v for v in value if isinstance(v, str) and v.strip()), None)
    return value.strip()[:maximum] if isinstance(value, str) and value.strip() else None


def _metadata(result, plan):
    if plan["operation"] == "dataset":
        return _dataset_metadata(result, plan)
    if not isinstance(result, dict) or result.get("status") != "success":
        raise ValueError("TOOLUNIVERSE_LOOKUP_FAILED")
    rows = result.get("data")
    if plan["operation"] == "doi":
        rows = [rows] if isinstance(rows, dict) else None
    if not isinstance(rows, list) or len(rows) > plan["limit"] or any(not isinstance(x, dict) for x in rows):
        raise ValueError("TOOLUNIVERSE_RESPONSE_SHAPE_INVALID")
    if plan["operation"] == "search" and result.get("count") != len(rows):
        raise ValueError("TOOLUNIVERSE_RESPONSE_COUNT_MISMATCH")
    papers, seen = [], set()
    for row in rows:
        doi = _text(row.get("DOI"), 250)
        if doi and not _DOI.fullmatch(doi):
            doi = None
        if doi and doi.casefold() in seen:
            continue
        if doi:
            seen.add(doi.casefold())
        published = row.get("published")
        dates = published.get("date-parts", []) if isinstance(published, dict) else []
        year = dates[0][0] if isinstance(dates, list) and dates and isinstance(dates[0], list) and dates[0] else None
        year = year if type(year) is int and 1000 <= year <= 2100 else None
        count = row.get("is-referenced-by-count")
        papers.append({"doi": doi, "title": _text(row.get("title"), 500),
                       "venue": _text(row.get("container-title"), 200), "year": year,
                       "citation_count_reported": count if type(count) is int and count >= 0 else None})
    if plan["operation"] == "doi" and (len(papers) != 1 or
            not papers[0]["doi"] or papers[0]["doi"].casefold() != plan["public_text"].casefold()):
        raise ValueError("TOOLUNIVERSE_DOI_RESPONSE_MISMATCH")
    total = result.get("total_count")
    total = total if type(total) is int and total >= len(rows) else None
    return {"papers": papers, "returned_count": len(rows), "unique_candidate_count": len(papers),
            "total_count_reported": total, "complete_literature_search": False,
            "primary_sources_verified": False, "novelty_verified": False}


def _dataset_metadata(result, plan):
    if not isinstance(result, dict) or result.get("status") != "success":
        raise ValueError("TOOLUNIVERSE_DATASET_LOOKUP_FAILED")
    data = result.get("data")
    hits = data.get("hits") if isinstance(data, dict) else None
    rows = hits.get("hits") if isinstance(hits, dict) else None
    if (not isinstance(rows, list) or len(rows) > plan["limit"]
            or result.get("count") != len(rows) or any(not isinstance(x, dict) for x in rows)):
        raise ValueError("TOOLUNIVERSE_DATASET_RESPONSE_SHAPE_INVALID")
    records, seen = [], set()
    for row in rows:
        meta = row.get("metadata")
        if not isinstance(meta, dict):
            continue
        resource = meta.get("resource_type")
        if not isinstance(resource, dict) or resource.get("type") != "dataset":
            continue
        record_id = row.get("id")
        if type(record_id) is not int or record_id <= 0 or record_id in seen:
            continue
        seen.add(record_id)
        doi = _text(row.get("doi") or meta.get("doi"), 250)
        if doi and not _DOI.fullmatch(doi):
            doi = None
        license_data = meta.get("license")
        license_id = _text(license_data.get("id"), 120) if isinstance(license_data, dict) else _text(license_data, 120)
        records.append({"record_id": record_id, "doi": doi,
                        "title": _text(meta.get("title"), 500),
                        "publication_date_reported": _text(meta.get("publication_date"), 30),
                        "version_reported": _text(meta.get("version"), 80),
                        "access_right_reported": _text(meta.get("access_right"), 80),
                        "license_id_reported": license_id})
    total = hits.get("total")
    if isinstance(total, dict):
        total = total.get("value") if total.get("relation") == "eq" else None
    total = total if type(total) is int and total >= len(rows) else None
    return {"datasets": records, "returned_count": len(rows), "unique_candidate_count": len(records),
            "total_count_reported": total, "dataset_scope_verified": False,
            "license_verified": False, "data_downloaded": False, "suitability_verified": False}


def query(plan, root, source_root, *, execute=False, ack_public_network=False, rules=()):
    checked = preview(plan, rules)
    if execute is not True or ack_public_network is not True:
        raise ValueError("TOOLUNIVERSE_EXPLICIT_PUBLIC_NETWORK_OPT_IN_REQUIRED")
    if checked["blocked_by_policy"]:
        raise ValueError("TOOLUNIVERSE_LOCAL_POLICY_DENIED")
    if source_root is None:
        raise ValueError("TOOLUNIVERSE_SOURCE_ROOT_REQUIRED")
    root = aide_pilot._check_root(root, exists=False)
    # A fresh root prevents overwriting or silently retrying an uncertain lookup.
    root.mkdir(exist_ok=False)
    aide_pilot._write(root / "request.json", aide_pilot._canonical(plan))
    result = _native_call(checked["native_call"], source_root)
    metadata = _metadata(result, plan)
    dataset = plan["operation"] == "dataset"
    record = {"schema_version": "tooluniverse-dataset-observation-v1" if dataset else "tooluniverse-literature-observation-v1",
              "upstream_revision": _REVISION, "plan_sha256": checked["plan_sha256"],
              "metadata": metadata, "literature_verified": False, "model_calls_requested": 0}
    aide_pilot._write(root / ("datasets.json" if dataset else "literature.json"), aide_pilot._canonical(record))
    return collect(plan, root, rules=rules)


def collect(plan, root, *, rules=()):
    checked = preview(plan, rules)
    root = aide_pilot._check_root(root, exists=True)
    if aide_pilot._read(root / "request.json", 32*1024) != aide_pilot._canonical(plan):
        raise ValueError("TOOLUNIVERSE_REQUEST_MISMATCH")
    dataset = plan["operation"] == "dataset"
    ref = "datasets.json" if dataset else "literature.json"
    raw = aide_pilot._read(root / ref, 128*1024)
    record = json.loads(raw)
    schema = "tooluniverse-dataset-observation-v1" if dataset else "tooluniverse-literature-observation-v1"
    if (not isinstance(record, dict) or record.get("schema_version") != schema
            or record.get("upstream_revision") != _REVISION or record.get("plan_sha256") != checked["plan_sha256"]
            or record.get("literature_verified") is not False):
        raise ValueError("TOOLUNIVERSE_OBSERVATION_MISMATCH")
    metadata = record.get("metadata")
    records_key = "datasets" if dataset else "papers"
    if not isinstance(metadata, dict) or not isinstance(metadata.get(records_key), list):
        raise ValueError("TOOLUNIVERSE_OBSERVATION_METADATA_INVALID")
    count = metadata.get("unique_candidate_count")
    returned = metadata.get("returned_count")
    total = metadata.get("total_count_reported")
    if (type(count) is not int or type(returned) is not int or
            not 0 <= count <= returned <= plan["limit"] or len(metadata[records_key]) != count
            or (total is not None and (type(total) is not int or total < returned))):
        raise ValueError("TOOLUNIVERSE_OBSERVATION_COUNT_INVALID")
    packet = {"schema_version": "specialist-intake-v1", "provider": "tooluniverse",
              "task": checked["task"], "plan_sha256_declared": checked["plan_sha256"],
              "agent_result": {"schema_version": "2.0", "project_id": plan["project_id"],
                   "task_id": plan["task_id"], "agent_id": "tooluniverse", "attempt_id": plan["attempt_id"],
                   "execution": {"status": "NEEDS_REVIEW", "budget_exhausted": False},
                   "deliverables": {"code_refs": [], "run_refs": [], "evidence_refs": [], "report_refs": [ref]},
                   "findings": [], "scientific_assessment": {"claim_status": "NOT_ASSESSED",
                       "protocol_status": "NOT_ASSESSED", "outcome": "NOT_ASSESSED", "review_required": True},
                   "unresolved_issues": (["Dataset metadata only; no file acquisition, license, ground truth, split or suitability verification."] if dataset else ["Bibliographic metadata only; no primary-source, coverage or novelty verification."]),
                   "next_action_candidates": (["Review candidate record, license, actual data schema, subjects, labels and independent split before H4."] if dataset else ["Review the candidate DOI/title records against original publications before H3 or contribution decisions."]),
                   "authorization_verified": False, "scientific_completion_verified": False},
              "artifact_observation": {"status": "PUBLIC_METADATA_BYTES_OBSERVED_ONLY",
                   "artifacts": [{"ref": ref, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}],
                   "artifact_ref_base": "OPERATOR_SELECTED_ISOLATED_ATTEMPT_ROOT",
                   "provider_summary": {"candidate_count": count, "returned_count": returned,
                                        "total_count_reported": total, **({"record_kind": "dataset"} if dataset else {})},
                   "process_completion_verified": False, "plan_binding_verified": False,
                   "scientific_validity_verified": False},
              "execution_authorized": False}
    return packet
