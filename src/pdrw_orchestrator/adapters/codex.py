"""Codex CLI adapter for a *synthetic fixture only*; no scientific projects.

Probe is no-cost. run_readonly_pilot is an actual external Codex subprocess,
only when a caller explicitly opts in after staging a one-time intent. It
uses Codex's read-only sandbox but is NOT a host-enforced read-scope or network
security boundary. Operators should run in an isolated environment.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import validate
from jsonschema.exceptions import ValidationError
from pdrw_orchestrator.contracts import render_pilot_contract

_MAX_OUTPUT_BYTES = 64 * 1024
# Pinned contents of the public synthetic pilot, NOT arbitrary repo files.
# Calculated on the exact UTF-8 bytes of the accepted fixture files.
_ALLOWED_FIXTURE_SHA256 = {
    "README.md": "1099ad13f6d0de6d253324a34616dd70cb389e25e74fe14c1ee8c8096b7de65f",
    "sensor_example.py": "8586e4ed8c8302d6cbdae34d3328683c096abdab723dafe6329c598636caf2c6",
}
_REQUIRED_FLAGS = (
    "--output-schema", "--output-last-message", "--sandbox",
    "--ignore-user-config", "--ignore-rules", "--ephemeral",
)


def fixture_root() -> Path:
    root = Path(__file__).resolve().parents[3] / "examples" / "codex-pilot"
    return root.resolve()


def output_schema_path() -> Path:
    return (Path(__file__).resolve().parents[3] /
            "schemas" / "codex-pilot-response.schema.json").resolve()


def resolve_codex_executable(executable: str | None = None) -> Path | None:
    candidate = executable or shutil.which("codex")
    if not candidate:
        return None
    path = Path(candidate).expanduser().resolve()
    if not path.is_file():
        return None
    # Windows npm .cmd/.bat shims may execute through cmd.exe even with shell=False.
    # Require the native .exe to keep argument boundaries deterministic.
    if os.name == "nt" and path.suffix.lower() != ".exe":
        return None
    if os.name != "nt" and not os.access(path, os.X_OK):
        return None
    return path


@dataclass(frozen=True)
class CodexProbe:
    status: str
    executable: str | None
    version: str | None
    supported: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status, "executable": self.executable,
            "version": self.version, "supported": self.supported,
            "credentials_verified": False,
            "real_model_task_executed": False,
            "host_isolation_verified": False,
        }


def probe_codex(executable: str | None = None) -> CodexProbe:
    path = resolve_codex_executable(executable)
    if path is None:
        return CodexProbe("BINARY_NOT_FOUND_OR_UNSAFE_SHIM", None, None, False)
    try:
        version = subprocess.run(
            [str(path), "--version"], capture_output=True, text=True,
            check=False, timeout=8,
        )
        help_result = subprocess.run(
            [str(path), "exec", "--help"], capture_output=True, text=True,
            check=False, timeout=8,
        )
    except (OSError, subprocess.TimeoutExpired):
        return CodexProbe("BINARY_PROBE_FAILED", str(path), None, False)
    version_text = version.stdout.strip()[:160] if version.returncode == 0 else None
    help_text = (help_result.stdout + help_result.stderr)[:20000]
    if version.returncode or help_result.returncode or not all(
        flag in help_text for flag in _REQUIRED_FLAGS
    ):
        return CodexProbe("INCOMPATIBLE_CLI_FLAGS", str(path), version_text, False)
    return CodexProbe("CLI_CAPABILITY_PROBE_OK", str(path), version_text, True)


def verify_fixture() -> Path:
    fixture = fixture_root()
    schema = output_schema_path()
    if not fixture.is_dir() or not schema.is_file():
        raise ValueError("PILOT_FIXTURE_OR_SCHEMA_MISSING")
    # Validate the actual checked-out fixture; no path from a model or task is accepted.
    root = Path(__file__).resolve().parents[3]
    if fixture.parent != root / "examples":
        raise ValueError("PILOT_FIXTURE_PATH_UNEXPECTED")
    entries = list(fixture.iterdir())
    if set(p.name for p in entries) != set(_ALLOWED_FIXTURE_SHA256):
        raise ValueError("PILOT_FIXTURE_ALLOWLIST_MISMATCH")
    for path in entries:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 24 * 1024:
            raise ValueError("PILOT_FIXTURE_FILE_UNSAFE")
        raw = path.read_bytes()
        # Windows Git checkout may use CRLF; normalize line endings only.
        # Reject any stray CR byte so that this does not weaken allowlisting.
        if b"\r" in raw.replace(b"\r\n", b""):
            raise ValueError("PILOT_FIXTURE_HASH_MISMATCH")
        normalized_bytes = raw.replace(b"\r\n", b"\n")
        if hashlib.sha256(normalized_bytes).hexdigest() != _ALLOWED_FIXTURE_SHA256[path.name]:
            raise ValueError("PILOT_FIXTURE_HASH_MISMATCH")
    return fixture


def pilot_prompt() -> str:
    return (
        "Review only the SYNTHETIC, non-sensitive sensor_example.py inside "
        "the configured fixture directory. Do not edit files, run training, "
        "access other directories or send any files to MCP tools. "
        "Identify concrete evaluation risks with source_refs relative to "
        "this fixture, distinguish observations from unverified hypotheses, "
        "and propose a minimal independent check. "
        "Return ONLY the JSON object matching the supplied output schema. "
        "No claims of scientific verification or execution authorization."
    )


def run_readonly_pilot(
    *,
    executable: str,
    output_path: Path,
    wall_seconds: int,
    task_contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """One real CLI process; caller must persist dispatch intent BEFORE calling."""
    if type(wall_seconds) is not int or not 10 <= wall_seconds <= 300:
        raise ValueError("INVALID_PILOT_WALL_BUDGET")
    path = resolve_codex_executable(executable)
    if path is None:
        raise ValueError("CODEX_EXECUTABLE_UNAVAILABLE")
    fixture = verify_fixture()
    schema_file = output_schema_path()
    output_path = output_path.resolve()
    if not output_path.parent.is_dir() or output_path.exists() or output_path.is_symlink():
        raise ValueError("PILOT_OUTPUT_PATH_UNAVAILABLE")
    # A second integrity check immediately before attempting the subprocess.
    # This does not replace VM-level isolation or prevent every TOCTOU race.
    verify_fixture()
    rendered_prompt = (render_pilot_contract(task_contract)
                       if task_contract is not None else pilot_prompt())
    args = [
        str(path), "exec",
        "--ephemeral", "--ignore-user-config", "--ignore-rules",
        "--sandbox", "read-only", "--ask-for-approval", "never",
        "--skip-git-repo-check", "-C", str(fixture),
        "--output-schema", str(schema_file),
        "--output-last-message", str(output_path),
        "-",
    ]
    try:
        proc = subprocess.run(
            args, input=rendered_prompt, text=True, check=False,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            timeout=wall_seconds,
        )
    except subprocess.TimeoutExpired:
        return {"status": "TIMEOUT_PROCESS_STATE_UNCERTAIN", "returncode": None,
                "report": None}
    except OSError:
        return {"status": "PROCESS_LAUNCH_FAILED_UNCERTAIN", "returncode": None,
                "report": None}
    if proc.returncode != 0:
        return {"status": "PROCESS_FAILED", "returncode": proc.returncode,
                "report": None}
    if not output_path.is_file() or output_path.is_symlink():
        return {"status": "NO_MACHINE_READABLE_OUTPUT", "returncode": 0,
                "report": None}
    if output_path.stat().st_size > _MAX_OUTPUT_BYTES:
        return {"status": "OUTPUT_EXCEEDS_LIMIT", "returncode": 0,
                "report": None}
    try:
        report = json.loads(output_path.read_text(encoding="utf-8"))
        schema = json.loads(schema_file.read_text(encoding="utf-8"))
        validate(instance=report, schema=schema)
    except (ValueError, UnicodeError, OSError, ValidationError, TypeError):
        return {"status": "INVALID_MACHINE_READABLE_OUTPUT", "returncode": 0,
                "report": None}
    # Model-output JSON schema uses a portable strict subset. Check limits
    # locally rather than relying on provider support for maxItems/maxLength.
    if (not report["summary"].strip() or len(report["summary"]) > 2000 or len(report["observations"]) > 8
            or len(report["limitations"]) > 8 or len(report["next_actions"]) > 5):
        return {"status": "INVALID_MACHINE_READABLE_OUTPUT", "returncode": 0, "report": None}
    for item in report["observations"]:
        if (not item["claim"].strip() or len(item["claim"]) > 1000 or
                len(item["source_refs"]) > 8 or len(item["limitations"]) > 8 or
                any(not ref.strip() or len(ref) > 200 for ref in item["source_refs"]) or
                any(not note.strip() or len(note) > 400 for note in item["limitations"])):
            return {"status": "INVALID_MACHINE_READABLE_OUTPUT", "returncode": 0, "report": None}
    if any(not s.strip() or len(s) > 400 for s in report["limitations"] + report["next_actions"]):
        return {"status": "INVALID_MACHINE_READABLE_OUTPUT", "returncode": 0, "report": None}
    return {"status": "STRUCTURED_OUTPUT_RECEIVED", "returncode": 0,
            "report": report}
