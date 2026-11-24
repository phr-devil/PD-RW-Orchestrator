"""Claude Code limited to public synthetic review, no tools or project input."""
from __future__ import annotations
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from jsonschema import validate, ValidationError
from .codex import output_schema_path, verify_fixture
from ..runtime.lifecycle import run_tracked_child

_FLAGS = ("--print", "--output-format", "--json-schema", "--tools",
          "--strict-mcp-config", "--safe-mode", "--no-session-persistence",
          "--max-turns", "--max-budget-usd", "--permission-mode", "--no-chrome")
_MAX = 65536
_SCHEMA_SHA256 = "8d7c098d0258f8e66955445b2b9d2f138d46ae8495568ea698939a3c57b0d495"


def load_review_schema():
    """Pin the exact public response contract, including all descriptions."""
    path = output_schema_path()
    if not path.is_file() or path.is_symlink():
        raise ValueError("RELAY_SCHEMA_UNAVAILABLE")
    with path.open("rb") as stream:
        raw = stream.read(_MAX + 1)
    if len(raw) > _MAX:
        raise ValueError("RELAY_SCHEMA_TOO_LARGE")
    schema = json.loads(raw)
    canonical = json.dumps(schema, sort_keys=True, separators=(",", ":")).encode()
    if hashlib.sha256(canonical).hexdigest() != _SCHEMA_SHA256:
        raise ValueError("RELAY_SCHEMA_CHANGED")
    return schema


def probe_claude(executable=None):
    candidate = executable or shutil.which("claude")
    if not candidate:
        return {"status": "CLAUDE_NOT_CONNECTED", "supported": False}
    path = Path(candidate).expanduser().resolve()
    if not path.is_file() or (os.name == "nt" and path.suffix.lower() != ".exe"):
        return {"status": "CLAUDE_NOT_CONNECTED", "supported": False}
    try:
        replies = []
        for flag in ("--version", "--help"):
            with tempfile.TemporaryFile(mode="w+b") as sink:
                p = subprocess.run([str(path), flag], stdout=sink, stderr=subprocess.DEVNULL,
                                   timeout=8, check=False)
                sink.seek(0)
                raw = sink.read(65537)
            if p.returncode or len(raw) > 65536:
                raise ValueError("probe failed")
            replies.append(raw.decode("utf-8"))
        if not all(re.search(r"(?<![\w-])" + re.escape(f) + r"(?![\w-])", replies[1])
                   for f in _FLAGS):
            raise ValueError("flags unavailable")
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return {"status": "CLAUDE_PROBE_FAILED", "supported": False}
    return {"status": "CLAUDE_PILOT_CAPABILITY_ONLY", "supported": True,
            "executable": str(path), "version": replies[0].strip()[:160],
            "credentials_verified": False, "general_research_ready": False,
            "host_isolation_verified": False}


def run_review(*, executable, prompt, output_path, lifecycle):
    """One bounded subprocess. All caller inputs originate from the fixed relay."""
    verify_fixture()
    schema = load_review_schema()
    args = [executable, "--print", "--output-format", "json", "--json-schema",
            json.dumps(schema, separators=(",", ":")), "--safe-mode",
            "--tools", "", "--strict-mcp-config", "--no-session-persistence",
            "--permission-mode", "dontAsk", "--no-chrome", "--max-turns", "3",
            "--max-budget-usd", "0.50"]
    with tempfile.TemporaryDirectory(prefix="pdrw-synthetic-review-") as cwd:
        with tempfile.TemporaryFile(mode="w+b") as sink:
            code, failure = run_tracked_child(args, prompt, 120, lifecycle,
                                              stdout=sink, cwd=cwd)
            sink.seek(0)
            raw = sink.read(_MAX+1)
    def result(status, code, report=None):
        return {"status": status, "returncode": code, "report": report}
    if failure:
        return result(failure, None)
    if code != 0:
        return result("PROCESS_FAILED", code)
    if len(raw) > _MAX:
        return result("OUTPUT_EXCEEDS_LIMIT", 0)
    try:
        wrapper = json.loads(raw)
        if not isinstance(wrapper, dict) or wrapper.get("is_error") is not False:
            raise ValueError("provider error")
        report = wrapper["structured_output"]
        validate(instance=report, schema=schema)
        if (not report["summary"].strip() or len(report["summary"]) > 2000
                or len(report["observations"]) > 8 or len(report["limitations"]) > 8
                or len(report["next_actions"]) > 5):
            raise ValueError("report limits")
        for item in report["observations"]:
            if (not item["claim"].strip() or len(item["claim"]) > 1000
                    or len(item["source_refs"]) > 8 or len(item["limitations"]) > 8
                    or any(not x.strip() or len(x)>200 for x in item["source_refs"])
                    or any(not x.strip() or len(x)>400 for x in item["limitations"])):
                raise ValueError("observation limits")
        if any(not x.strip() or len(x)>400 for x in report["limitations"]+report["next_actions"]):
            raise ValueError("report limits")
        with output_path.open("xb") as f:
            f.write(json.dumps(report, ensure_ascii=False).encode("utf-8"))
    except (ValueError, KeyError, TypeError, ValidationError, OSError):
        return result("INVALID_MACHINE_READABLE_OUTPUT", 0)
    return result("STRUCTURED_OUTPUT_RECEIVED", 0, report)
