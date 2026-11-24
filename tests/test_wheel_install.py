"""Wheel/zip resource smoke test: no external Agent, no research data.

Builds a *regular* Wheel (not editable), extracts into an isolated directory,
then runs built-in no-model CLI commands from the extracted package.
"""
import os
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = (
    "configs/agents.example.yaml",
    "policies/user/research-guidance.example.yaml",
    "examples/codex-pilot/README.md",
    "examples/codex-pilot/sensor_example.py",
    "schemas/codex-pilot-response.schema.json",
)


def test_bundled_resources_match_checked_out_sources():
    bundle = ROOT / "src" / "pdrw_orchestrator" / "bundled"
    for relative in FILES:
        a = (ROOT / relative).read_bytes().replace(b"\r\n", b"\n")
        b = (bundle / relative).read_bytes().replace(b"\r\n", b"\n")
        assert a == b, relative


def test_regular_wheel_supports_contract_and_fixed_fixture(tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    build = subprocess.run(
        [sys.executable, "-m", "pip", "wheel", "--no-deps", "--wheel-dir",
         str(dist), str(ROOT)],
        cwd=tmp_path, capture_output=True, text=True, timeout=120, check=False,
    )
    assert build.returncode == 0, build.stderr[-3000:]
    wheels = list(dist.glob("pdrw_orchestrator-*.whl"))
    assert len(wheels) == 1
    extracted = tmp_path / "isolated"
    extracted.mkdir()
    with zipfile.ZipFile(wheels[0]) as wheel:
        names = set(wheel.namelist())
        for relative in FILES:
            assert "pdrw_orchestrator/bundled/" + relative in names
        wheel.extractall(extracted)
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(extracted)
    environment["PDRW_ORCH_RUNTIME_DIR"] = str(tmp_path / "private-runtime")
    for key in ("PDRW_RUNTIME_DIR", "PDRW_AGENT_CONFIG", "PDRW_WORKFLOW_ROOT", "PDRW_CASE_LIBRARY_ROOT"):
        environment.pop(key, None)
    script = (
        "from pdrw_orchestrator.assets import data_root;"
        "from pdrw_orchestrator.adapters.codex import verify_fixture,output_schema_path;"
        "from pdrw_orchestrator.cli import main;"
        "assert data_root().name == 'bundled',data_root();"
        "assert verify_fixture().is_dir();"
        "assert output_schema_path().is_file();"
        "assert main(['codex','contract']) == 0;"
        "from pdrw_orchestrator.runtime.store import stage_plan,inspect_plan;"
        "from pdrw_orchestrator.models import TaskPacket;"
        "t=TaskPacket('T','P','review','Synthetic',idempotency_key='T-key');"
        "assert stage_plan('wheel',(t,))['status']=='STAGED_NOT_AUTHORIZED';"
        "assert inspect_plan('P','wheel')['uncertain_intent_count']==0"
    )
    launched = subprocess.run(
        [sys.executable, "-c", script], cwd=tmp_path, env=environment,
        capture_output=True, text=True, timeout=30, check=False,
    )
    assert launched.returncode == 0, launched.stderr[-4000:]
    assert "PILOT_CONTRACT_PREVIEW_ONLY" in launched.stdout
