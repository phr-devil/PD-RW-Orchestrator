import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from pdrw_orchestrator.integrations.pdrw import inspect_resume


def configured(tmp_path):
    rule_dir = tmp_path / "workflow"
    rule_dir.mkdir()
    (rule_dir / "AGENTS.md").write_text("rules", encoding="utf-8")
    (rule_dir / "WORKFLOW.md").write_text("workflow", encoding="utf-8")
    project_map = tmp_path / "project-map.json"
    project_map.write_text('{"schema_version":1,"projects":{}}', encoding="utf-8")
    return {"PDRW_AGENT_CONFIG": str(project_map), "PDRW_WORKFLOW_ROOT": str(rule_dir)}


def test_not_configured_does_not_run(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("must not execute")
    monkeypatch.setattr(subprocess, "run", fail)
    assert inspect_resume("19", environment={})["bridge_status"] == "PDRW_NOT_CONFIGURED"


def test_invalid_project_id_rejected_before_run(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("must not execute")
    monkeypatch.setattr(subprocess, "run", fail)
    assert inspect_resume("19; rm -rf /")["bridge_status"] == "INVALID_PROJECT_ID"
    assert inspect_resume("../protected")["bridge_status"] == "INVALID_PROJECT_ID"


def test_bounded_cli_preserves_resume_status_without_raw_data(tmp_path, monkeypatch):
    env = configured(tmp_path)
    payload = {
        "status": "SOURCE_REVIEW_REQUIRED",
        "scientific_resume_status": "SOURCE_REVIEW_REQUIRED",
        "project_id": "19",
        "snapshot_excerpt": "DO_NOT_EXPOSE_RAW_RESEARCH",
        "scientific_context": {"active_task_id_declared": "P1"},
        "operation_context": {"unresolved": [], "operational_reconciliation_required": False},
        "next_action_hint": {"action": "REVIEW_ORIGINAL_SCOPE_THEN_CONTINUE_PERMITTED_DEV",
                             "execution_authorized": False},
        "rule_commit_local_only": "sha-local",
    }
    seen = {}
    def mock_run(argv, **kwargs):
        seen["argv"] = argv
        assert kwargs["timeout"] <= 90
        assert kwargs["check"] is False
        assert kwargs["env"]["PDRW_AGENT_CONFIG"] == env["PDRW_AGENT_CONFIG"]
        return SimpleNamespace(stdout=json.dumps(payload), returncode=0)
    monkeypatch.setattr(subprocess, "run", mock_run)
    result = inspect_resume("19", environment=env, python_executable=sys.executable)
    assert seen["argv"][-4:] == ["pdrw_agent.cli", "resume", "--project-id", "19"]
    assert result["bridge_status"] == "SOURCE_REVIEW_ONLY"
    assert result["active_task_id_declared"] == "P1"
    assert result["authorization_verified"] is False
    assert result["project_identity_authenticated"] is False
    assert "DO_NOT_EXPOSE_RAW_RESEARCH" not in json.dumps(result)


def test_unresolved_prior_attempt_is_not_permission(tmp_path, monkeypatch):
    env = configured(tmp_path)
    payload = {"status": "NEEDS_OPERATIONAL_RECONCILIATION", "project_id": "42",
               "scientific_context": {},
               "operation_context": {"unresolved": [{"operation_id": "x", "recovery_class": "VERIFY_ACTUAL_EXECUTION"}],
                                     "operational_reconciliation_required": True},
               "next_action_hint": {"action": "RECONCILE_UNCERTAIN_PRIOR_OPERATION"}}
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: SimpleNamespace(
        stdout=json.dumps(payload), returncode=0))
    result = inspect_resume("42", environment=env)
    assert result["unresolved_operation_count"] == 1
    assert result["operational_reconciliation_required"] is True
    assert result["restart_permitted"] is False


@pytest.mark.parametrize("response,exit_code,expected", [
    ({"status": "SOURCE_REVIEW_REQUIRED", "project_id": "44"}, 0, "UPSTREAM_PROJECT_ID_MISMATCH"),
    ({"status": "ERROR", "error_code": "PROJECT_NOT_REGISTERED"}, 2, "UPSTREAM_ERROR"),
    ("oops", 0, "UPSTREAM_INVALID_CONTRACT"),
])
def test_upstream_errors_fail_closed(tmp_path, monkeypatch, response, exit_code, expected):
    env = configured(tmp_path)
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: SimpleNamespace(
        stdout=json.dumps(response), returncode=exit_code))
    assert inspect_resume("19", environment=env)["bridge_status"] == expected


def test_timeout_reports_without_retry(tmp_path, monkeypatch):
    env = configured(tmp_path)
    attempts = []
    def timed_out(*a, **k):
        attempts.append(True)
        raise subprocess.TimeoutExpired(["python"], 10)
    monkeypatch.setattr(subprocess, "run", timed_out)
    result = inspect_resume("19", environment=env)
    assert result["bridge_status"] == "UPSTREAM_TIMEOUT_NO_RETRY"
    assert len(attempts) == 1


def test_oversized_output_is_refused(tmp_path, monkeypatch):
    env = configured(tmp_path)
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: SimpleNamespace(
        stdout="X" * (256 * 1024 + 1), returncode=0))
    assert inspect_resume("19", environment=env)["bridge_status"] == "UPSTREAM_OUTPUT_TOO_LARGE"
