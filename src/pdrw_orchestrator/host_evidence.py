"""Local execution artifact consistency. This is NOT scientific verification.

Compares a host-created receipt to its exact contract and captured output.
The receipt and files live in the same user-controlled machine, so this only
checks local byte consistency; neither provenance nor independent validity.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .contracts import canonical_contract, contract_sha256

_MAX_OUTPUT_BYTES = 64 * 1024
_MAX_RECEIPT_BYTES = 12 * 1024
_MAX_CONTRACT_BYTES = 12 * 1024


def _checked_bytes(path: Path, maximum: int) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ValueError("HOST_ARTIFACT_MISSING_OR_SYMLINK")
    if path.stat().st_size > maximum:
        raise ValueError("HOST_ARTIFACT_TOO_LARGE")
    return path.read_bytes()


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_pilot_contract(run_dir: Path, contract: dict[str, Any]) -> Path:
    path = run_dir / "task-contract.json"
    payload = canonical_contract(contract)
    if len(payload) > _MAX_CONTRACT_BYTES or path.exists() or path.is_symlink():
        raise ValueError("PILOT_CONTRACT_FILE_INVALID")
    with path.open("xb") as stream:
        stream.write(payload)
    return path


def write_pilot_receipt(
    run_dir: Path, *, contract: dict[str, Any],
    project_id: str, task_id: str, attempt_id: str,
    invocation: dict[str, Any], codex_version: str | None,
) -> dict[str, Any]:
    output_path = run_dir / "codex-final.json"
    output_sha = None
    if output_path.exists() or output_path.is_symlink():
        output_sha = _digest(_checked_bytes(output_path, _MAX_OUTPUT_BYTES))
    status = invocation.get("status")
    code = invocation.get("returncode")
    if not isinstance(status, str) or (code is not None and type(code) is not int):
        raise ValueError("INVALID_HOST_INVOCATION")
    receipt = {
        "schema_version": "1.0",
        "origin": "LOCAL_SUBPROCESS_OBSERVATION",
        "project_id": project_id,
        "task_id": task_id,
        "attempt_id": attempt_id,
        "dispatch_attempted": True,
        "outcome": status,
        "process_returncode": code,
        "contract_sha256": contract_sha256(contract),
        "structured_output_sha256": output_sha,
        "codex_version_probed": codex_version,
        "captured_utc": datetime.now(timezone.utc).isoformat(),
        "external_model_usage_verified": False,
        "scientific_completion_verified": False,
        "authorization_verified": False,
    }
    payload = (json.dumps(receipt, sort_keys=True, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if len(payload) > _MAX_RECEIPT_BYTES:
        raise ValueError("HOST_RECEIPT_OVERSIZE")
    with (run_dir / "host-execution.json").open("xb") as stream:
        stream.write(payload)
    return receipt


def inspect_pilot_receipt(
    run_dir: Path, *, project_id: str, task_id: str,
    attempt_id: str, expected_contract_sha256: str | None = None,
) -> dict[str, Any]:
    """Read-only byte reconciliation; never returns a trusted science/grant state."""
    try:
        run_dir = Path(run_dir)
        if run_dir.is_symlink() or not run_dir.is_dir():
            raise ValueError("HOST_RUN_DIRECTORY_INVALID")
        receipt = json.loads(_checked_bytes(
            run_dir / "host-execution.json", _MAX_RECEIPT_BYTES))
        contract_data = _checked_bytes(run_dir / "task-contract.json", _MAX_CONTRACT_BYTES)
        contract = json.loads(contract_data)
        if (receipt.get("schema_version") != "1.0" or
                receipt.get("origin") != "LOCAL_SUBPROCESS_OBSERVATION" or
                receipt.get("project_id") != project_id or
                receipt.get("task_id") != task_id or
                receipt.get("attempt_id") != attempt_id or
                receipt.get("dispatch_attempted") is not True or
                receipt.get("authorization_verified") is not False or
                receipt.get("scientific_completion_verified") is not False or
                receipt.get("external_model_usage_verified") is not False):
            raise ValueError("HOST_RECEIPT_IDENTITY_INVALID")
        actual_sha = _digest(contract_data)
        if actual_sha != contract_sha256(contract) or actual_sha != receipt.get("contract_sha256"):
            raise ValueError("HOST_CONTRACT_HASH_MISMATCH")
        if expected_contract_sha256 is not None and actual_sha != expected_contract_sha256:
            raise ValueError("HOST_EXPECTED_CONTRACT_MISMATCH")
        expected_output = receipt.get("structured_output_sha256")
        output_file = run_dir / "codex-final.json"
        if expected_output is None:
            if output_file.exists() or output_file.is_symlink():
                raise ValueError("HOST_UNRECORDED_OUTPUT_PRESENT")
            state = "LOCAL_RECEIPT_MATCH_NO_OUTPUT"
        else:
            actual_output = _digest(_checked_bytes(output_file, _MAX_OUTPUT_BYTES))
            if actual_output != expected_output:
                raise ValueError("HOST_OUTPUT_HASH_MISMATCH")
            state = "LOCAL_BYTES_MATCH_NOT_SCIENCE"
        return {
            "status": state,
            "contract_sha256": actual_sha,
            "structured_output_sha256": expected_output,
            "local_byte_consistency_checked": True,
            "original_pd_rw_evidence_verified": False,
            "authorization_verified": False,
            "scientific_completion_verified": False,
            "restart_permitted": False,
        }
    except (OSError, UnicodeError, ValueError, TypeError, KeyError):
        return {
            "status": "HOST_RECEIPT_RECONCILIATION_REQUIRED",
            "local_byte_consistency_checked": False,
            "original_pd_rw_evidence_verified": False,
            "authorization_verified": False,
            "scientific_completion_verified": False,
            "restart_permitted": False,
        }
