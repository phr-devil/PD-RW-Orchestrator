"""Read-only installed PD-RW-Experience adapter; P4 advice only."""
from __future__ import annotations
import hashlib
import json
import re
import subprocess
import tempfile
from datetime import date
from pathlib import Path

from pdrw_orchestrator.policy import Guidance, experience_rules

_VERSION = "0.2.0a1"
_FILES = ("lessons", "cases", "receipts", "trusted_public_key", "source_index")
_FIELDS = {"id", "level", "source", "text", "task_types", "evidence_refs", "conditions"}
_MAX_REPLY = 32768
_ENTRY = (
    "import importlib.metadata as m,sys;"
    "sys.exit(3) if m.version('pdrw-experience')!='0.2.0a1' else None;"
    "from pdrw_experience.cli import main;"
    "sys.exit(main(sys.argv[1:]))"
)


def accept_advisories(items: list[dict]) -> tuple[Guidance, ...]:
    return experience_rules(items)


def _read(path, limit):
    if not path.is_file() or path.is_symlink():
        raise ValueError("EXPERIENCE_FILE_UNAVAILABLE")
    with path.open("rb") as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise ValueError("EXPERIENCE_FILE_TOO_LARGE")
    return data


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _config(path):
    raw = _read(Path(path), 16384)
    obj = json.loads(raw.decode("utf-8-sig"))
    if not isinstance(obj, dict) or set(obj) != {
        "schema_version", "python", "source_root", "public_key_sha256", *_FILES
    } or obj["schema_version"] != "1.0":
        raise ValueError("EXPERIENCE_CONFIG_INVALID")
    result = {}
    for key in ("python", "source_root", *_FILES):
        value = obj[key]
        if not isinstance(value, str) or not Path(value).is_absolute():
            raise ValueError("EXPERIENCE_ABSOLUTE_HOST_PATH_REQUIRED")
        p = Path(value)
        if p.is_symlink() or not (p.is_dir() if key == "source_root" else p.is_file()):
            if key != "python" or not p.is_file():
                raise ValueError("EXPERIENCE_HOST_PATH_UNAVAILABLE")
        result[key] = p
    fingerprint = obj["public_key_sha256"]
    if not isinstance(fingerprint, str) or not re.fullmatch("[0-9a-f]{64}", fingerprint):
        raise ValueError("EXPERIENCE_KEY_PIN_INVALID")
    result["key_pin"] = fingerprint
    result["config_sha256"] = _sha(raw)
    return result


def _snapshot(cfg):
    hashes = {}
    for key in _FILES:
        limit = 16384 if key == "trusted_public_key" else 16 * 1024 * 1024
        hashes[key] = _sha(_read(cfg[key], limit))
    if hashes["trusted_public_key"] != cfg["key_pin"]:
        raise ValueError("EXPERIENCE_KEY_PIN_MISMATCH")
    return hashes


def _items(payload, task_type, limit):
    if not isinstance(payload, list) or len(payload) > limit:
        raise ValueError("EXPERIENCE_RESPONSE_INVALID")
    seen = set()
    for item in payload:
        if (not isinstance(item, dict) or set(item) != _FIELDS
                or item["level"] != "experience"):
            raise ValueError("EXPERIENCE_RESPONSE_INVALID")
        for field, maximum in (("id", 160), ("source", 512), ("text", 1200)):
            if (not isinstance(item[field], str) or not item[field].strip()
                    or len(item[field]) > maximum):
                raise ValueError("EXPERIENCE_RESPONSE_INVALID")
        if (not item["source"].startswith("PD-RW-Experience:")
                or ":attested_review:" not in item["source"]
                or item["id"] in seen):
            raise ValueError("EXPERIENCE_RESPONSE_INVALID")
        seen.add(item["id"])
        for field, maximum in (("task_types", 16), ("evidence_refs", 16), ("conditions", 8)):
            values = item[field]
            if (not isinstance(values, list) or len(values) > maximum
                    or any(not isinstance(v, str) or not v.strip() or len(v) > 500 for v in values)):
                raise ValueError("EXPERIENCE_RESPONSE_INVALID")
        if task_type not in item["task_types"] or not item["evidence_refs"]:
            raise ValueError("EXPERIENCE_RESPONSE_SCOPE_MISMATCH")
    return accept_advisories(payload)


def retrieve_for_task(task, *, config_path, query, as_of, limit=3):
    """One local retrieval; an error is distinct from no matching lesson."""
    base = {
        "status": "EXPERIENCE_UNAVAILABLE", "task_id": task.task_id,
        "task_type": task.task_type, "provider_version_required": _VERSION,
        "retrieved_count": 0, "provider_attestation_independently_verified": False,
        "applicability_verified": False, "scientific_truth_verified": False,
        "permission_granted": False, "automatic_lesson_update": False,
        "model_calls_requested": 0,
    }
    try:
        if (not isinstance(query, str) or not query.strip()
                or len(query.encode("utf-8")) > 512
                or not isinstance(as_of, str) or date.fromisoformat(as_of).isoformat() != as_of
                or type(limit) is not int or not 1 <= limit <= 3):
            raise ValueError("EXPERIENCE_REQUEST_INVALID")
        base["as_of"] = as_of
        base["query_sha256"] = _sha(query.encode("utf-8"))
        cfg = _config(config_path)
        before = _snapshot(cfg)
        argv = [str(cfg["python"]), "-I", "-B", "-c", _ENTRY, "retrieve",
                str(cfg["lessons"]), "--cases", str(cfg["cases"]),
                "--task-type=" + task.task_type, "--query=" + query,
                "--as-of=" + as_of, "--limit", str(limit),
                "--receipts", str(cfg["receipts"]),
                "--trusted-public-key", str(cfg["trusted_public_key"]),
                "--source-root", str(cfg["source_root"]),
                "--source-index", str(cfg["source_index"])]
        with tempfile.TemporaryFile(mode="w+b") as sink:
            p = subprocess.run(argv, stdout=sink, stderr=subprocess.DEVNULL,
                               timeout=30, check=False)
            sink.seek(0)
            raw = sink.read(_MAX_REPLY + 1)
        if p.returncode:
            return (), {**base, "status": "EXPERIENCE_PROVIDER_BLOCKED"}
        if len(raw) > _MAX_REPLY:
            return (), {**base, "status": "EXPERIENCE_RESPONSE_OVERSIZE"}
        if _config(config_path) != cfg or _snapshot(cfg) != before:
            return (), {**base, "status": "EXPERIENCE_INPUT_CHANGED"}
        rules = _items(json.loads(raw.decode("utf-8-sig")), task.task_type, limit)
        return rules, {**base,
            "status": "EXPERIENCE_ADVISORIES_RECEIVED" if rules else "EXPERIENCE_NO_MATCH",
            "retrieved_count": len(rules), "retrieved_rule_ids": [r.id for r in rules],
            "provider_response_sha256": _sha(raw),
            "config_sha256": cfg["config_sha256"], "catalog_sha256": before,
        }
    except subprocess.TimeoutExpired:
        return (), {**base, "status": "EXPERIENCE_TIMEOUT_NO_RETRY"}
    except (OSError, ValueError, TypeError, KeyError, UnicodeError):
        return (), {**base, "status": "EXPERIENCE_REQUEST_OR_RESPONSE_REJECTED"}
