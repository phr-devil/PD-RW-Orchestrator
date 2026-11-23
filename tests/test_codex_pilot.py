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
                   "--ignore-user-config --ignore-rules --ephemeral\n",
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
    assert first["model_invoked_confirmed"] is False
    assert first["structured_cli_output_received"] is True
    assert first["external_model_usage_verified"] is False
    assert first["decision_type"] == "REVIEW_OUTCOME_PENDING"
    assert first["science_validated"] is False
    assert first["execution_authorized_for_research"] is False
    assert first["restart_permitted"] is False
    files = first["private_report"]
    report = json.loads(Path(files["handoff_json"]).read_text(encoding="utf-8"))
    assert report["result"]["scientific_assessment"]["effective_claim_status"] == "NOT_ASSESSED"
    assert report["result"]["agent_id"] == "codex-local"
    assert report["previous_execution"]["origin"] == "LOCAL_SUBPROCESS_OBSERVATION"
    assert report["previous_execution"]["dispatch_attempted"] is True
    assert report["next_dispatch_performed"] is False
    assert report["dispatch_scope"] == "NEXT_TASK_ONLY"
    assert Path(first["host_receipt_ref"]).is_file()
    assert report["previous_execution"]["scientific_completion_verified"] is False
    assert report["next_task"]["task_type"] == "human_assessment"
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


def test_fixture_bytes_tampered_fail_closed(monkeypatch):
    original = Path.read_bytes
    fixture = codex.fixture_root()
    def fake_read(path):
        if path == fixture / "sensor_example.py":
            return b"private-data-substituted-into-public-synthetic-fixture"
        return original(path)
    monkeypatch.setattr(Path, "read_bytes", fake_read)
    with pytest.raises(ValueError, match="PILOT_FIXTURE_HASH_MISMATCH"):
        codex.verify_fixture()


def test_extra_unlisted_fixture_file_rejected_without_writing_files(monkeypatch, tmp_path):
    original = Path.iterdir
    fixture = codex.fixture_root()
    def forged_listing(path):
        entries = list(original(path))
        if path == fixture:
            return iter(entries + [tmp_path / "extra.txt"])
        return iter(entries)
    monkeypatch.setattr(Path, "iterdir", forged_listing)
    with pytest.raises(ValueError, match="PILOT_FIXTURE_ALLOWLIST_MISMATCH"):
        codex.verify_fixture()


def test_bad_policy_preflight_rejects_before_any_subprocess(tmp_path, monkeypatch):
    monkeypatch.setenv("PDRW_ORCH_RUNTIME_DIR", str(tmp_path / "runtime"))
    monkeypatch.setattr(codex_pilot, "probe_codex", lambda arg: codex.CodexProbe(
        "CLI_CAPABILITY_PROBE_OK", str(Path(sys.executable)), "fake", True))
    monkeypatch.setattr(codex_pilot, "run_readonly_pilot", lambda **kw:
                        (_ for _ in ()).throw(AssertionError("model should not be called")))
    invalid = tmp_path / "wrong-policy.yaml"
    invalid.write_text("schema_version: '1.0'\nrules: [corrupt-value]\n", encoding="utf-8")
    with pytest.raises(ValueError):
        codex_pilot.run_codex_pilot(
            plan_id="bad-policy", attempt_id="test-attempt",
            codex_bin=str(Path(sys.executable)), policy_path=invalid,
            registry_path=ROOT / "configs/agents.example.yaml")
    assert not (tmp_path / "runtime").exists()


def test_bad_registry_preflight_rejects_before_dispatch(tmp_path, monkeypatch):
    monkeypatch.setenv("PDRW_ORCH_RUNTIME_DIR", str(tmp_path / "runtime"))
    monkeypatch.setattr(codex_pilot, "probe_codex", lambda arg: codex.CodexProbe(
        "CLI_CAPABILITY_PROBE_OK", str(Path(sys.executable)), "fake", True))
    monkeypatch.setattr(codex_pilot, "run_readonly_pilot", lambda **kw:
                        (_ for _ in ()).throw(AssertionError("model should not be called")))
    invalid = tmp_path / "bad-registry.yaml"
    invalid.write_text("agents: unknown\n", encoding="utf-8")
    with pytest.raises(ValueError):
        codex_pilot.run_codex_pilot(
            plan_id="bad-registry", attempt_id="test-attempt",
            codex_bin=str(Path(sys.executable)),
            policy_path=ROOT / "policies/user/research-guidance.example.yaml",
            registry_path=invalid)
    assert not (tmp_path / "runtime").exists()


def test_invalid_string_limits_refused_by_codex_even_if_schema_is_valid(tmp_path, monkeypatch):
    monkeypatch.setattr(codex, "resolve_codex_executable", lambda _: Path(sys.executable))
    long = fake_report()
    long["observations"][0]["source_refs"] = ["x" * 300]
    def bad_result(args, **kw):
        Path(args[args.index("--output-last-message") + 1]).write_text(
            json.dumps(long), encoding="utf-8")
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(codex.subprocess, "run", bad_result)
    result = codex.run_readonly_pilot(
        executable=str(Path(sys.executable)),
        output_path=tmp_path / "out.json", wall_seconds=120)
    assert result["status"] == "INVALID_MACHINE_READABLE_OUTPUT"


def test_windows_crlf_checkout_preserves_fixture_integrity(monkeypatch):
    original = Path.read_bytes
    fixture = codex.fixture_root()
    def to_crlf(path):
        raw = original(path)
        if path == fixture / "sensor_example.py":
            return raw.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
        return raw
    monkeypatch.setattr(Path, "read_bytes", to_crlf)
    assert codex.verify_fixture() == fixture


def test_subprocess_returned_but_invalid_result_keeps_host_receipt(tmp_path, monkeypatch):
    monkeypatch.setenv("PDRW_ORCH_RUNTIME_DIR", str(tmp_path / "runtime"))
    monkeypatch.setattr(codex_pilot, "probe_codex", lambda _: codex.CodexProbe(
        "CLI_CAPABILITY_PROBE_OK", str(Path(sys.executable)), "synthetic", True))
    def malformed(**kw):
        kw["output_path"].write_text('{"summary":"partial"}', encoding="utf-8")
        return {"status": "STRUCTURED_OUTPUT_RECEIVED", "returncode": 0,
                "report": {"summary": "partial"}}
    monkeypatch.setattr(codex_pilot, "run_readonly_pilot", malformed)
    kwargs = {
        "plan_id": "invalid-result-no-retry", "attempt_id": "attempt-001",
        "codex_bin": str(Path(sys.executable)),
        "policy_path": ROOT / "policies/user/research-guidance.example.yaml",
        "registry_path": ROOT / "configs/agents.example.yaml",
    }
    with pytest.raises(KeyError):
        codex_pilot.run_codex_pilot(**kwargs)
    host_receipt = tmp_path / "runtime" / "codex-pilot" / kwargs["plan_id"] / kwargs["attempt_id"] / "host-execution.json"
    assert host_receipt.is_file()
    receipt = json.loads(host_receipt.read_text(encoding="utf-8"))
    assert receipt["dispatch_attempted"] is True
    assert receipt["scientific_completion_verified"] is False
    assert codex_pilot.run_codex_pilot(**kwargs)["status"] == "ALREADY_RESERVED_NO_RETRY"
