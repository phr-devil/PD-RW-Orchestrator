"""Limited AutoResearchClaw discovery preview and candidate artifact intake.

The native pipeline can have effects even before stage 5. No actual invocation
or approval is provided. Returned literature is unverified.
"""
import hashlib
import json
import re
from pathlib import Path

import yaml

from .aide import _plain
from ..specialists import candidates

_FIELDS = {"schema_version", "project_id", "task_id", "attempt_id", "public_topic",
           "research_scope", "max_papers", "config_sha256"}
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}\Z")
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_FILES = ("stage-01/goal.md", "stage-02/problem_tree.md",
          "stage-03/search_plan.yaml", "stage-03/queries.json",
          "stage-04/candidates.jsonl", "stage-04/search_meta.json",
          "pipeline_summary.json")
_LIMIT = 4 * 1024 * 1024


def preview_arc(plan):
    if not isinstance(plan, dict) or set(plan) != _FIELDS or plan.get("schema_version") != "arc-discovery-preview-v1":
        raise ValueError("ARC_PLAN_INVALID")
    for key in ("project_id", "task_id", "attempt_id"):
        if not isinstance(plan[key], str) or not _ID.fullmatch(plan[key]):
            raise ValueError("ARC_ID_INVALID")
    for key in ("public_topic", "research_scope"):
        if not isinstance(plan[key], str) or not plan[key].strip() or len(plan[key]) > 2000 or "\0" in plan[key]:
            raise ValueError("ARC_TEXT_INVALID")
    if plan["public_topic"].lstrip().startswith("-"):
        raise ValueError("ARC_TOPIC_OPTION_INVALID")
    if type(plan["max_papers"]) is not int or not 1 <= plan["max_papers"] <= 30:
        raise ValueError("ARC_PAPER_TARGET_INVALID")
    if not isinstance(plan["config_sha256"], str) or not _SHA.fullmatch(plan["config_sha256"]):
        raise ValueError("ARC_CONFIG_HASH_INVALID")
    raw = json.dumps(plan, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    topic = plan["public_topic"] + "\nResearch constraints: " + plan["research_scope"] + "\nReturn discovery candidates only; do not infer novelty or author approval."
    revision = next(p["revision"] for p in candidates()["candidates"] if p["id"] == "arc")
    return {"status": "ARC_DISCOVERY_PREVIEW_ONLY", "project_id": plan["project_id"],
            "task_id": plan["task_id"], "attempt_id": plan["attempt_id"],
            "plan_sha256": hashlib.sha256(raw).hexdigest(), "upstream_revision": revision,
            "argv_preview": ["researchclaw", "run", "--config", "config.arc.yaml",
                "--output", "run", "--from-stage", "TOPIC_INIT", "--to-stage", "LITERATURE_COLLECT",
                "--no-graceful-degradation", "--topic", topic],
            "environment_preview": {"PYTHONUTF8": "1"},
            "config_sha256_declared": plan["config_sha256"],
            "paper_target_declared_not_enforced": plan["max_papers"],
            "required_host_checks": [
                "Use fresh private output and approved public topic/scope only; topic and config may be transmitted.",
                "Compare exact approved config bytes, set project.mode non-auto, disable HITL auto approval, external KB, MetaClaw and external integrations.",
                "Use simulated experiment mode, no SSH, no GPU setup or installation; inspect startup and post-pipeline hooks.",
                "Authorize literature/network/model costs; restrict egress and filesystem; do not expose credentials or private project data.",
                "Review native output; real search flags and citations may still be inaccurate; no H3/H4/H6 approval."],
            "expected_artifacts": list(_FILES), "stage_ceiling": 4,
            "hard_budget_enforced": False, "config_binding_verified": False,
            "execution_authorized": False, "execute_performed": False,
            "model_calls_requested": 0}


def _read(root, ref):
    path = root / ref
    if path.parent != root:
        _plain(path.parent, directory=True)
    _plain(path, directory=False)
    with path.open("rb") as stream:
        raw = stream.read(_LIMIT + 1)
    if not raw or len(raw) > _LIMIT:
        raise ValueError("ARC_ARTIFACT_SIZE_INVALID")
    return raw


def collect_arc(plan, root):
    preview = preview_arc(plan)
    root = Path(root)
    if not root.is_absolute() or ".." in root.parts:
        raise ValueError("ARC_ROOT_ABSOLUTE_REQUIRED")
    for part in reversed((root, *root.parents)):
        _plain(part, directory=True)
    # Reject visible later-stage artifacts; absence is not proof of effects.
    for item in root.iterdir():
        if re.fullmatch(r"stage-[0-9]+", item.name) and int(item.name.split("-")[1]) > 4:
            raise ValueError("ARC_STAGE_CEILING_EXCEEDED")
    raws = {ref: _read(root, ref) for ref in _FILES}
    summary = json.loads(raws["pipeline_summary.json"])
    meta = json.loads(raws["stage-04/search_meta.json"])
    if not isinstance(summary, dict) or not isinstance(meta, dict):
        raise ValueError("ARC_SUMMARY_INVALID")
    if any(type(summary.get(k)) is not int or summary[k] != v for k, v in {
        "from_stage": 1, "final_stage": 4, "stages_executed": 4, "stages_done": 4,
        "stages_failed": 0, "stages_blocked": 0, "stages_paused": 0}.items()) or summary.get("final_status") != "done" or summary.get("degraded") is not False:
        raise ValueError("ARC_DISCOVERY_INCOMPLETE_OR_DEGRADED")
    rows = []
    for line in raws["stage-04/candidates.jsonl"].splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError("ARC_CANDIDATE_INVALID")
        rows.append(row)
        if len(rows) > 1000:
            raise ValueError("ARC_CANDIDATE_CAP_EXCEEDED")
    if type(meta.get("total_candidates")) is not int or meta["total_candidates"] != len(rows):
        raise ValueError("ARC_CANDIDATE_COUNT_MISMATCH")
    placeholder_count = sum(row.get("is_placeholder") is True for row in rows)
    artifacts = [{"ref": ref, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
                 for ref, raw in raws.items()]
    return {"status": "ARC_DISCOVERY_ARTIFACTS_OBSERVED_ONLY",
            "plan_sha256_declared": preview["plan_sha256"], "artifacts": artifacts,
            "candidate_count": len(rows), "declared_placeholder_count": placeholder_count,
            "real_search_reported": meta.get("real_search") is True,
            "literature_verified": False, "novelty_verified": False, "process_completion_verified": False,
            "plan_binding_verified": False, "execution_authorized": False, "model_calls_requested": 0,
            "agent_result": {"schema_version": "2.0", "project_id": plan["project_id"],
                "task_id": plan["task_id"], "agent_id": "arc", "attempt_id": plan["attempt_id"],
                "execution": {"status": "NEEDS_REVIEW", "budget_exhausted": False},
                "deliverables": {"code_refs": [], "run_refs": [], "report_refs": list(_FILES), "evidence_refs": []},
                "findings": [], "scientific_assessment": {"claim_status": "NOT_ASSESSED",
                    "protocol_status": "NOT_ASSESSED", "outcome": "NOT_ASSESSED", "review_required": True},
                "unresolved_issues": ["Source existence, retrieval provenance, closest prior and novelty are unverified.",
                    "Placeholder/fallback literature must not count as evidence.",
                    "Artifact paths are relative to the isolated ARC output, not original project Runs."],
                "next_action_candidates": ["Independently verify primary literature, compare alternatives, then prepare author H3 options."],
                "authorization_verified": False, "scientific_completion_verified": False}}


def discovery_config_issues(raw, max_papers):
    """Check a small set of known startup hazards in the reviewed YAML.

    Not a substitute for native config loading, host isolation or a hard budget.
    Never return config values (the upstream CLI copies YAML to its run output).
    """
    try:
        data = yaml.safe_load(raw)
    except (yaml.YAMLError, UnicodeError, RecursionError):
        return ["ARC_CONFIG_YAML_INVALID"]
    if not isinstance(data, dict):
        return ["ARC_CONFIG_YAML_INVALID"]

    def get(*path):
        value = data
        for key in path:
            if not isinstance(value, dict):
                return None
            value = value.get(key)
        return value

    issues = []
    if get("project", "mode") not in ("docs-first", "semi-auto") or get("project", "profile") not in (None, ""):
        issues.append("ARC_CONFIG_AUTO_OR_PROFILE")
    if get("knowledge_base", "backend") != "markdown" or get("knowledge_base", "root") != "kb" or get("knowledge_base", "obsidian_vault") not in (None, ""):
        issues.append("ARC_CONFIG_KB_NOT_LOCAL")
    if get("experiment", "mode") != "simulated" or get("experiment", "sandbox", "gpu_required") not in (None, False):
        issues.append("ARC_CONFIG_EXPERIMENT_MODE")
    for section in ("memory", "skills", "knowledge_graph", "metaclaw_bridge", "overleaf", "web_search"):
        if get(section, "enabled") is not False:
            issues.append("ARC_CONFIG_DISABLE_" + section.upper())
    for key in ("use_cron", "use_message", "use_memory", "use_sessions_spawn", "use_web_fetch", "use_browser"):
        if get("openclaw_bridge", key) not in (None, False):
            issues.append("ARC_CONFIG_BRIDGE_ENABLED")
            break
    if get("mcp", "server_enabled") not in (None, False) or get("mcp", "external_servers") not in (None, []):
        issues.append("ARC_CONFIG_MCP_ENABLED")
    if get("hitl", "enabled") not in (None, False) or get("security", "allow_publish_without_approval") not in (None, False):
        issues.append("ARC_CONFIG_HITL_OR_PUBLISH")
    if get("notifications", "channel") != "console" or get("notifications", "target") not in (None, ""):
        issues.append("ARC_CONFIG_NOTIFICATION")
    for path in (("llm", "api_key"), ("llm", "reviewer_api_key"), ("llm", "s2_api_key"),
                 ("literature_search", "openalex_api_key"), ("literature_search", "s2_api_key"),
                 ("web_search", "tavily_api_key"), ("metaclaw_bridge", "fallback_api_key")):
        if get(*path) not in (None, ""):
            issues.append("ARC_CONFIG_INLINE_CREDENTIAL")
            break
    for path in (("research", "daily_paper_count"), ("literature_search", "max_results_per_query")):
        val = get(*path)
        if type(val) is not int or not 1 <= val <= max_papers:
            issues.append("ARC_CONFIG_PAPER_TARGET_MISMATCH")
            break
    return issues
