"""M2-Pilot: command contract and real-path unit tests, no model calls."""
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from jsonschema import validate

from pdrw_orchestrator.adapters import codex
from pdrw_orchestrator.cli import main
from pdrw_orchestrator.runtime import codex_pilot
from pdrw_orchestrator.runtime.store import inspect_plan

ROOT = Path(__file__).resolve().parents[1]


def fake_report():
    return {
        "summary": "Synthetic pressure frames overlap in random splitting.",
        "observations": [{
            "claim": "Adjacent frames could appear in different groups.",
            "source_refs": ["sensor_example.py:7-13"],
            "limitations": ["Not demonstrated on independent subjects"],
        }],
        "limitations": ["Only a synthetic teaching example"],
        "next_actions": ["Consider grouping by sequence before splitting"],
    }


def test_schema_matches_structured_example():
    schema = json.loads((ROOT / "schemas/codex-pilot-response.schema.json").read_text())
    validate(instance=fake_report(), schema=schema)


def test_codex_probe_has_no_model_call(monkeypatch):
    monkeypatch.setattr(codex, "resolve_codex_executable", lambda candidate=None: Path(sys.executable))
    calls = []

    def run(args, **kw):
        calls.append(args)
        if args[-1] == "--version":
            return SimpleNamespace(stdout="codex-cli 1.0\n", stderr="", returncode=0)
        return SimpleNamespace(
            stdout="--output-schema --output-last-message --sandbox "
                   "--ignore-user-config --ephemeral\n",
            stderr="", returncode=0,
        )

    monkeypatch.setattr(codex.subprocess, "run", run)
    p = codex.probe_codex()
    assert p.supported
    assert p.status == "CLI_CAPABILITY_PROBE_OK"
    assert calls == [[str(Path(sys.executable)), "--version"],
                     [str(Path(sys.executable)), "exec", "--help"]]
    assert p.to_dict()["real_model_task_executed"] is False
    assert p.to_dict()["credentials_verified"] is False


def test_codex_command_readonly_and_structured_output(tmp_path, monkeypatch):
    monkeypatch.setattr(codex, "resolve_codex_executable", lambda _: Path(sys.executable))
    output = tmp_path / "codex-final.json"
    calls = []

    def run(args, **kw):
        calls.append((args, kw))
        assert args[:2] == [str(Path(sys.executable)), "exec"]
        assert args[-1] == "-"
        assert args[args.index("--sandbox") + 1] == "read-only"
        assert args[args.index("--ask-for-approval") + 1] == "never"
        assert args[args.index("-C") + 1] == str(codex.fixture_root())
        assert args[args.index("--output-schema") + 1] == str(codex.output_schema_path())
        assert "--ignore-user-config" in args and "--ephemeral" in args
        assert "--yolo" not in args and "--add-dir" not in args
        assert kw["timeout"] == 120 and kw["check"] is False
        assert "SYNTHETIC" in kw["input"] and "Do not edit" in kw["input"]
        assert "shell" not in kw
        Path(args[args.index("--output-last-message") + 1]).write_text(json.dumps(fake_report()))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(codex.subprocess, "run", run)
    answer = codex.run_readonly_pilot(
        executable=str(Path(sys.executable)), output_path=output, wall_seconds=120
    )
    assert answer["status"] == "STRUCTURED_OUTPUT_RECEIVED"
    assert answer["report"]["observations"][0]["claim"].startswith("Adjacent")
    assert len(calls) == 1


def test_cli_pilot_requires_two_explicit_flags(capsys, monkeypatch):
    monkeypatch.setattr(codex_pilot, "run_readonly_pilot", lambda **kw: (_ for _ in ()).throw(
        AssertionError("must not run without opt-in")
    ))
    for argv in (
        ["codex", "pilot", "--plan-id", "demo", "--attempt-id", "first"],
        ["codex", "pilot", "--plan-id", "demo", "--attempt-id", "first", "--execute"],
        ["codex", "pilot", "--plan-id", "demo", "--attempt-id", "first", "--ack-external-model"],
    ):
        assert main(argv) == 2
        assert "EXPLICIT_MODEL_OPT_IN_REQUIRED" in capsys.readouterr().out


def test_end_to_end_simulated_codex_result_and_one_attempt(tmp_path, monkeypatch):
    """The provider is simulated; persistent orchestration and handoff are real."""
    monkeypatch.setenv("PDRW_ORCH_RUNTIME_DIR", str(tmp_path / "runtime"))
    monkeypatch.setattr(codex_pilot, "probe_codex", lambda path: codex.CodexProbe(
        "CLI_CAPABILITY_PROBE_OK", str(Path(sys.executable)), "fake-test", True
    ))
    invoked = []

    def fake_invoke(*, executable, output_path, wall_seconds):
        invoked.append((executable, output_path, wall_seconds))
        output_path.write_text(json.dumps(fake_report()), encoding="utf-8")
        return {
            "status": "STRUCTURED_OUTPUT_RECEIVED",
            "returncode": 0,
            "report": fake_report(),
        }

    monkeypatch.setattr(codex_pilot, "run_readonly_pilot", fake_invoke)
    kw = {
        "plan_id": "m2pilot-one", "attempt_id": "trial-001",
        "codex_bin": str(Path(sys.executable)),
        "policy_path": ROOT / "policies/user/research-guidance.example.yaml",
        "registry_path": ROOT / "configs/agents.example.yaml",
    }
    first = codex_pilot.run_codex_pilot(**kw)
    assert first["status"] == "STRUCTURED_OUTPUT_RECEIVED"
    assert first["model_invocation_attempted"] is True
    assert first["model_invoked_confirmed"] is True
    assert first["decision_type"] == "INDEPENDENT_REVIEW"
    assert first["science_validated"] is False
    assert first["execution_authorized_for_research"] is False
    assert first["restart_permitted"] is False
    files = first["private_report"]
    report = json.loads(Path(files["handoff_json"]).read_text(encoding="utf-8"))
    assert report["result"]["scientific_assessment"]["effective_claim_status"] == "NOT_ASSESSED"
    assert report["result"]["agent_id"] == "codex-local"
    assert "independently" in report["next_task"]["objective"].lower()
    assert Path(files["handoff_md"]).is_file()
    assert len(invoked) == 1
    assert inspect_plan("PILOT", "m2pilot-one")["status"] == "RECONCILIATION_REQUIRED"
    again = codex_pilot.run_codex_pilot(**kw)
    assert again["status"] == "ALREADY_RESERVED_NO_RETRY"
    assert len(invoked) == 1


def test_timeout_keeps_attempt_uncertain_no_retry(tmp_path, monkeypatch):
    monkeypatch.setenv("PDRW_ORCH_RUNTIME_DIR", str(tmp_path / "runtime"))
    monkeypatch.setattr(codex_pilot, "probe_codex", lambda path: codex.CodexProbe(
        "CLI_CAPABILITY_PROBE_OK", str(Path(sys.executable)), "fake-test", True
    ))
    called = []
    def timeout(**kw):
        called.append(True)
        return {"status": "TIMEOUT_PROCESS_STATE_UNCERTAIN",
                "returncode": None, "report": None}
    monkeypatch.setattr(codex_pilot, "run_readonly_pilot", timeout)
    args = {
        "plan_id": "timeout-001", "attempt_id": "trial-one",
        "codex_bin": str(Path(sys.executable)),
        "policy_path": ROOT / "policies/user/research-guidance.example.yaml",
        "registry_path": ROOT / "configs/agents.example.yaml",
    }
    output = codex_pilot.run_codex_pilot(**args)
    assert output["status"] == "TIMEOUT_PROCESS_STATE_UNCERTAIN"
    assert output["decision_type"] == "RECONCILE"
    assert codex_pilot.run_codex_pilot(**args)["status"] == "ALREADY_RESERVED_NO_RETRY"
    assert len(called) == 1


def test_codex_probe_not_connected_fails_closed(monkeypatch):
    monkeypatch.setattr(codex_pilot, "probe_codex", lambda path: codex.CodexProbe(
        "BINARY_NOT_FOUND_OR_UNSAFE_SHIM", None, None, False
    ))
    monkeypatch.setattr(codex_pilot, "run_readonly_pilot", lambda **kw: (_ for _ in ()).throw(
        AssertionError("must not run")
    ))
    result = codex_pilot.run_codex_pilot(
        plan_id="no-binary", attempt_id="once", codex_bin=None,
        policy_path=ROOT / "policies/user/research-guidance.example.yaml",
        registry_path=ROOT / "configs/agents.example.yaml",
    )
    assert result["status"] == "NOT_CONNECTED"
    assert result["model_invoked"] is False


@pytest.mark.parametrize("bad", ["", "oops", "[]", "{\"summary\":\"bad\"}"])
def test_invalid_model_output_never_becomes_science(tmp_path, monkeypatch, bad):
    monkeypatch.setattr(codex, "resolve_codex_executable", lambda _: Path(sys.executable))
    def run(args, **kw):
        Path(args[args.index("--output-last-message")+1]).write_text(bad, encoding="utf-8")
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(codex.subprocess, "run", run)
    assert codex.run_readonly_pilot(
        executable=str(Path(sys.executable)), output_path=tmp_path/"out.json",
        wall_seconds=120
    )["status"] == "INVALID_MACHINE_READABLE_OUTPUT"


def test_invalid_worktree_cannot_be_user_supplied():
    # The runner takes only a fixed fixture. It has no --cwd/--task-file override.
    assert codex.fixture_root().is_dir()
    assert "codex-pilot" == codex.fixture_root().name
    assert codex.verify_fixture() == codex.fixture_root()
