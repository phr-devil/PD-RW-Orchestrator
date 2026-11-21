import json

from pdrw_orchestrator.cli import main


def test_schedule_cli_restart_and_no_dispatch(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("PDRW_ORCH_RUNTIME_DIR", str(tmp_path / "private-runtime"))
    from pathlib import Path
    source = Path(__file__).resolve().parents[1] / "examples/operational-plan.example.json"
    assert main(["schedule", "stage", "--file", str(source)]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "STAGED_NOT_AUTHORIZED"
    args = ["schedule", "inspect", "--project-id", "EXAMPLE", "--plan-id", "demo-research-001"]
    assert main(args) == 0
    first = json.loads(capsys.readouterr().out)
    assert first["status"] == "STAGED_NOT_AUTHORIZED"
    assert first["restart_permitted"] is False
    reserve = ["schedule", "mark-uncertain", "--project-id", "EXAMPLE",
               "--plan-id", "demo-research-001", "--task-id", "DISCOVERY-1",
               "--attempt-id", "example-attempt"]
    assert main(reserve) == 0
    recorded = json.loads(capsys.readouterr().out)
    assert recorded["dispatch_performed"] is False
    assert main(args) == 0
    after = json.loads(capsys.readouterr().out)
    assert after["status"] == "RECONCILIATION_REQUIRED"
    assert after["restart_permitted"] is False


def test_schedule_cli_unconfigured_is_error_without_side_effect(capsys, monkeypatch):
    monkeypatch.delenv("PDRW_ORCH_RUNTIME_DIR", raising=False)
    assert main(["schedule", "inspect", "--project-id", "P19", "--plan-id", "p1"]) == 2
    assert "PDRW_ORCH_RUNTIME_DIR_REQUIRED" in capsys.readouterr().out
