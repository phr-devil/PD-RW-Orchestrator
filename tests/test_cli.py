import json
from pdrw_orchestrator.cli import main


def test_cli_demo(capsys):
    assert main(["demo"]) == 0
    value = json.loads(capsys.readouterr().out)
    assert value["mode"] == "MOCK_ONLY"
    assert len(value["results"]) == 2


def test_cli_policy_check(capsys):
    assert main(["policy", "check"]) == 0
    value = json.loads(capsys.readouterr().out)
    assert value["status"] == "SHAPE_OK_ONLY"


def test_cli_doctor_truthful(capsys):
    assert main(["doctor"]) == 0
    value = json.loads(capsys.readouterr().out)
    assert value["external_agents_ready"] is False
    assert value["trusted_host_authorizer"] is False
