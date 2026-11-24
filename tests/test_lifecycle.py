"""Real synthetic child and lifecycle consistency tests; never invoke a model."""
import json
import sys
from pathlib import Path

import pytest

from pdrw_orchestrator.runtime.lifecycle import (
    PilotLifecycle, inspect_lifecycle, run_tracked_child, lifecycle_matches_invocation,
)
from pdrw_orchestrator.runtime.codex_pilot import pilot_task
from pdrw_orchestrator.runtime.store import stage_plan, mark_intent_uncertain, has_exact_intent
from pdrw_orchestrator.contracts import compile_pilot_contract, contract_sha256
from pdrw_orchestrator.policy import compile_guidance, load_policy
from pdrw_orchestrator.host_evidence import write_pilot_contract, write_pilot_receipt, inspect_pilot_receipt

ROOT = Path(__file__).resolve().parents[1]


def prepared(directory):
    task = pilot_task()
    contract = compile_pilot_contract(task, compile_guidance(task, load_policy(
        ROOT / "policies/user/research-guidance.example.yaml")))
    write_pilot_contract(directory, contract)
    args = dict(plan_id="plan1", attempt_id="try1", contract_sha256=contract_sha256(contract))
    return PilotLifecycle(directory, **args), args, contract


def test_real_child_exit_and_chain(tmp_path):
    journal, args, _ = prepared(tmp_path)
    code, err = run_tracked_child([sys.executable, "-I", "-c", "import sys; sys.stdin.read()"],
                                  "synthetic", 10, journal)
    assert (code, err) == (0, None)
    checked = inspect_lifecycle(tmp_path, **args)
    assert checked["status"] == "LIFECYCLE_DIRECT_CHILD_EXIT_RECORDED"
    assert lifecycle_matches_invocation(checked, "STRUCTURED_OUTPUT_RECEIVED", 0)
    assert not lifecycle_matches_invocation(checked, "STRUCTURED_OUTPUT_RECEIVED", 1)
    assert checked["original_operation_binding_verified"] is False
    assert checked["restart_permitted"] is False
    assert inspect_lifecycle(tmp_path, **{**args, "attempt_id": "other"})["status"] == "LIFECYCLE_RECONCILIATION_REQUIRED"


def test_actual_timeout_only_direct_child(tmp_path):
    journal, args, _ = prepared(tmp_path)
    code, err = run_tracked_child([sys.executable, "-I", "-c", "import time; time.sleep(30)"],
                                  "", 1, journal)
    assert code is None and err == "TIMEOUT_PROCESS_STATE_UNCERTAIN"
    checked = inspect_lifecycle(tmp_path, **args)
    assert checked["status"] == "LIFECYCLE_TIMEOUT_RECORDED"
    assert checked["descendant_processes_verified"] is False
    assert checked["restart_permitted"] is False


def test_launch_failure_recorded(tmp_path):
    journal, args, _ = prepared(tmp_path)
    code, err = run_tracked_child([str(tmp_path / "nonexistent-executable")], "", 10, journal)
    assert code is None and err == "PROCESS_LAUNCH_FAILED_UNCERTAIN"
    assert inspect_lifecycle(tmp_path, **args)["status"] == "LIFECYCLE_LAUNCH_FAILED_RECORDED"


def test_partial_or_tampered_journal_never_allows_retry(tmp_path):
    journal, args, _ = prepared(tmp_path)
    journal.record("launch-intent", {"wall_seconds": 10})
    assert inspect_lifecycle(tmp_path, **args)["status"] == "LIFECYCLE_RECONCILIATION_REQUIRED"
    journal.record("child-started", {"pid": 123, "identity": None})
    journal.record("child-ended", {"outcome": "EXITED", "returncode": 0})
    path = tmp_path / "child-started.json"
    row = json.loads(path.read_text())
    row["pid"] = 456
    path.write_text(json.dumps(row))
    assert inspect_lifecycle(tmp_path, **args)["status"] == "LIFECYCLE_RECONCILIATION_REQUIRED"
    with pytest.raises(FileExistsError):
        journal.record("launch-intent", {"wall_seconds": 10})


def test_oversize_output_does_not_erase_execution_receipt(tmp_path):
    _, _, contract = prepared(tmp_path)
    (tmp_path / "codex-final.json").write_bytes(b"x" * (65536 + 1))
    receipt = write_pilot_receipt(tmp_path, contract=contract, project_id="PILOT",
        task_id="CODEX-READ-001", attempt_id="try1", codex_version="synthetic",
        invocation={"status":"OUTPUT_EXCEEDS_LIMIT", "returncode":0})
    assert receipt["output_state"] == "UNREADABLE_OR_OVERSIZE"
    assert (tmp_path / "host-execution.json").is_file()
    assert inspect_pilot_receipt(tmp_path, project_id="PILOT", task_id="CODEX-READ-001",
        attempt_id="try1")["status"] == "HOST_RECEIPT_RECONCILIATION_REQUIRED"


def test_intent_lookup_requires_exact_attempt(tmp_path, monkeypatch):
    monkeypatch.setenv("PDRW_ORCH_RUNTIME_DIR", str(tmp_path / "runtime"))
    stage_plan("plan1", (pilot_task(),))
    assert not has_exact_intent("PILOT","plan1","CODEX-READ-001","try1")
    mark_intent_uncertain("PILOT","plan1","CODEX-READ-001","try1")
    assert has_exact_intent("PILOT","plan1","CODEX-READ-001","try1")
    assert not has_exact_intent("PILOT","plan1","CODEX-READ-001","try2")



def test_runtime_attempt_directory_rejects_redirected_parent(tmp_path):
    from pdrw_orchestrator.runtime.store import pilot_attempt_dir
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    other = tmp_path / "other"
    other.mkdir()
    try:
        (runtime / "codex-pilot").symlink_to(other, target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation unavailable on this host")
    with pytest.raises(ValueError, match="PILOT_ATTEMPT_PATH_REDIRECTED"):
        pilot_attempt_dir(runtime, "plan1", "try1")
    assert list(other.iterdir()) == []


def test_runtime_db_redirect_rejected(tmp_path, monkeypatch):
    from pdrw_orchestrator.runtime.store import _store_path
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    outside = tmp_path / "outside.sqlite"
    outside.write_bytes(b"untouched")
    try:
        (runtime / "orchestrator.sqlite").symlink_to(outside)
    except OSError:
        pytest.skip("symlink creation unavailable on this host")
    monkeypatch.setenv("PDRW_ORCH_RUNTIME_DIR", str(runtime))
    with pytest.raises(ValueError, match="RUNTIME_DATABASE_REDIRECTED"):
        _store_path(create=False)
    assert outside.read_bytes() == b"untouched"
