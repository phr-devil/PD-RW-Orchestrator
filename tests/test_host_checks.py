"""Host-only M1-C checks. Real local synthetic process, no model or research data."""
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from pdrw_orchestrator.runtime import host_checks as host
from pdrw_orchestrator.cli import main

SHA = "a" * 64


def fake_install(monkeypatch, version="1.0.0rc1", source="1.0.0rc1", digest=SHA):
    calls = []
    def fake(args, **kw):
        calls.append(args)
        assert args[:4] == [str(Path(sys.executable).absolute()), "-I", "-B", "-c"]
        assert kw["stderr"] == subprocess.DEVNULL
        kw["stdout"].write(json.dumps({
            "package_version": version, "source_version": source,
            "cli_sha256": digest}).encode())
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(host.subprocess, "run", fake)
    return calls


def test_probe_checks_metadata_and_source_in_selected_interpreter(monkeypatch):
    calls = fake_install(monkeypatch)
    result = host.probe_installation(expected_cli_sha256=SHA)
    assert len(calls) == 1
    assert result["status"] == "HOST_INSTALLATION_MATCHED_LOCALLY"
    assert result["cli_reference_matched"] is True
    assert result["full_revision_authenticated"] is False
    assert result["skill_mcp_alignment_verified"] is False
    assert result["execution_authorized"] is False


def test_stale_metadata_stops_before_original_source(monkeypatch):
    fake_install(monkeypatch, version="0.9.3")
    monkeypatch.setattr(host, "inspect_source_chain", lambda *a, **kw: pytest.fail("source called"))
    result = host.audit_host("P19")
    assert result["status"] == "HOST_INSTALLATION_RECONCILIATION_REQUIRED"
    assert result["installation"]["status"] == "HOST_VERSION_MISMATCH"
    assert result["new_author_grant_required"] is None


def test_cli_reference_hash_mismatch_stops_before_original_source(monkeypatch):
    fake_install(monkeypatch)
    monkeypatch.setattr(host, "inspect_source_chain", lambda *a, **kw: pytest.fail("source called"))
    result = host.audit_host("P19", expected_cli_sha256="b" * 64)
    assert result["installation"]["status"] == "HOST_CLI_HASH_MISMATCH"
    assert result["author_scope_verified"] is False


def mock_source(**extra):
    return {"project_id": "P19", "verification_status": "SOURCE_READ_ONLY_CHECKS_COMPLETE",
            "operation": {"task_id_declared": "T1"}, "run": None, **extra}


def test_host_audit_matches_source_task_but_not_permission(monkeypatch):
    calls = fake_install(monkeypatch)
    monkeypatch.setattr(host, "inspect_source_chain", lambda *a, **kw: mock_source())
    result = host.audit_host("P19", operation_id="OP1", task_id="T1")
    assert result["status"] == "HOST_READ_ONLY_CHECKS_COMPLETE"
    assert len(calls) == 2
    for key in ("execution_authorized", "author_scope_verified",
                "scientific_validity_verified", "restart_permitted",
                "operation_process_binding_verified", "project_identity_authenticated"):
        assert result[key] is False
    assert result["authorization_status"] == "EXISTING_SCOPE_VERIFIER_UNAVAILABLE"
    assert result["new_author_grant_required"] is None


def test_host_audit_rejects_unrelated_task_and_project(monkeypatch):
    fake_install(monkeypatch)
    monkeypatch.setattr(host, "inspect_source_chain", lambda *a, **kw: mock_source())
    assert host.audit_host("P19", task_id="T2")["status"] == "HOST_SOURCE_TASK_MISMATCH_OR_UNKNOWN"
    monkeypatch.setattr(host, "inspect_source_chain", lambda *a, **kw: mock_source(project_id="OTHER"))
    assert host.audit_host("P19")["status"] == "HOST_SOURCE_IDENTITY_MISMATCH"


def test_installation_change_during_audit_invalidates_join(monkeypatch):
    states = iter([
        {"status": "HOST_INSTALLATION_MATCHED_LOCALLY", "cli_sha256": SHA},
        {"status": "HOST_INSTALLATION_MATCHED_LOCALLY", "cli_sha256": "b" * 64},
    ])
    monkeypatch.setattr(host, "probe_installation", lambda **kw: next(states))
    monkeypatch.setattr(host, "inspect_source_chain", lambda *a, **kw: mock_source())
    result = host.audit_host("P19")
    assert result["status"] == "HOST_INSTALLATION_CHANGED_DURING_CHECK"
    assert result["source"] is None
    assert result["restart_permitted"] is False


def test_actual_local_synthetic_process_identity_and_no_restart():
    proc = subprocess.Popen([sys.executable, "-I", "-c", "import time; time.sleep(30)"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        observed = host.inspect_process(proc.pid)
        assert observed["status"] == "PROCESS_OBSERVED_UNBOUND", observed
        identity = observed["identity"]
        assert observed["same_process_as_baseline"] is False
        assert observed["operation_process_binding_verified"] is False
        options = {"expected_created_at": identity["created_at"],
                   "expected_exe_path_sha256": identity["exe_path_sha256"]}
        matched = host.inspect_process(proc.pid, **options)
        assert matched["status"] == "PROCESS_MATCH_ALIVE", matched
        assert matched["process_liveness_verified"] is True
        assert matched["restart_permitted"] is False
        assert matched["cancel_permitted"] is False
        mismatch = host.inspect_process(
            proc.pid, **{**options, "expected_created_at": identity["created_at"] - 10})
        assert mismatch["status"] == "PROCESS_IDENTITY_MISMATCH"
        assert mismatch["same_process_as_baseline"] is False
    finally:
        proc.terminate()
        proc.wait(timeout=10)
    absent = host.inspect_process(proc.pid, **options)
    assert absent["status"] in ("PROCESS_ABSENT_AT_SAMPLE", "PROCESS_IDENTITY_MISMATCH")
    assert absent["restart_permitted"] is False


def test_process_baseline_requires_both_values():
    assert host.inspect_process(os.getpid(), expected_created_at=1000.0)["status"] == "PROCESS_BASELINE_INVALID"
    assert host.inspect_process(-1)["status"] == "PROCESS_INPUT_INVALID"
    assert host.inspect_process(os.getpid(), expected_created_at=float("nan"),
                                expected_exe_path_sha256=SHA)["status"] == "PROCESS_BASELINE_INVALID"


def test_process_access_denied_stays_unknown(monkeypatch):
    import psutil
    def denied(*args, **kw):
        raise psutil.AccessDenied()
    monkeypatch.setattr(psutil, "Process", denied)
    result = host.inspect_process(os.getpid())
    assert result["status"] == "PROCESS_STATE_UNKNOWN"
    assert result["process_liveness_verified"] is False
    assert result["restart_permitted"] is False


def test_host_cli_process_observes_only_local_pid(capsys):
    assert main(["host", "process", "--pid", str(os.getpid())]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "PROCESS_OBSERVED_UNBOUND"
    assert result["operation_process_binding_verified"] is False
    assert result["execution_authorized"] is False


def test_host_cli_audit_reports_nonzero_if_no_matching_installation(monkeypatch, capsys):
    from pdrw_orchestrator import cli
    monkeypatch.setattr(cli, "audit_host", lambda *a, **kw: {
        "status": "HOST_INSTALLATION_RECONCILIATION_REQUIRED",
        "execution_authorized": False})
    assert main(["host", "audit", "--project-id", "P19"]) == 3
    assert json.loads(capsys.readouterr().out)["execution_authorized"] is False
