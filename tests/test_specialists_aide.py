import json
from pathlib import Path

import pytest

from pdrw_orchestrator.adapters.aide import collect_aide, preview_aide
from pdrw_orchestrator.agent_result import normalize_result
from pdrw_orchestrator.cli import main
from pdrw_orchestrator.models import TaskPacket
from pdrw_orchestrator.specialists import candidates


def plan():
    return {"schema_version": "aide-dev-preview-v1", "project_id": "P", "task_id": "T",
            "attempt_id": "a-1", "goal": "Synthetic regression", "evaluation": "Fixed grouped DEV RMSE",
            "protocol_ref": "PROTOCOL", "data_manifest_sha256": "a" * 64,
            "steps": 3, "step_timeout_seconds": 60, "metric_maximize": False,
            "code_provider": "openai", "code_model": "model-a",
            "feedback_provider": "anthropic", "feedback_model": "model-b"}


def test_catalog_not_readiness():
    result = candidates("optimization")
    assert [x["id"] for x in result["candidates"]] == ["aide"]
    assert result["selected_provider"] is None
    assert not result["candidates"][0]["execution_eligible"]
    assert not candidates("nonexistent")["candidates"]


def test_aide_preview_is_native_bounded_and_deterministic():
    p = plan()
    a = preview_aide(p)
    assert a == preview_aide(dict(reversed(list(p.items()))))
    assert a["argv_preview"][0] == "aide"
    assert "agent.steps=3" in a["argv_preview"]
    assert "generate_report=false" in a["argv_preview"]
    assert "agent.data_preview=false" in a["argv_preview"]
    assert not a["execution_authorized"] and not a["hard_total_budget_enforced"]
    assert a["model_calls_requested"] == 0
    assert preview_aide(dict(p, steps=4))["plan_sha256"] != a["plan_sha256"]


@pytest.mark.parametrize("change", [{"steps": 6}, {"steps": True}, {"step_timeout_seconds": 121},
    {"attempt_id": "../bad"}, {"data_manifest_sha256": "x"}, {"metric_maximize": 1},
    {"code_model": "${bad}"}, {"feedback_provider": "unknown"}, {"approved": True}])
def test_invalid_plan(change):
    with pytest.raises(ValueError):
        preview_aide(dict(plan(), **change))


def test_collect_is_untrusted_and_compatible(tmp_path):
    root = tmp_path.resolve()
    run = root / "logs" / "0-a-1"
    run.mkdir(parents=True)
    (run / "best_solution.py").write_text("raise RuntimeError('never execute')", encoding="utf-8")
    (run / "journal.json").write_text("{}", encoding="utf-8")
    result = collect_aide(plan(), root, "0-a-1")
    assert len(result["artifacts"]) == 2 and not result["plan_binding_verified"]
    assert not result["process_completion_verified"]
    raw = result["agent_result"]
    assert raw["deliverables"]["run_refs"] == []
    normalized = normalize_result(raw, TaskPacket(task_id="T", project_id="P", task_type="analysis", objective="Review"))
    assert normalized["execution"]["reported_status"] == "NEEDS_REVIEW"
    assert not normalized["scientific_completion_verified"]
    with pytest.raises(ValueError):
        collect_aide(plan(), root, "0-another")
    (run / "journal.json").write_text("", encoding="utf-8")
    with pytest.raises(ValueError):
        collect_aide(plan(), root, "0-a-1")


def test_cli(tmp_path, capsys):
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(plan()), encoding="utf-8")
    assert main(["aide", "preview", "--plan-file", str(path)]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "AIDE_PREVIEW_ONLY"
    assert main(["specialists", "select", "--capability", "optimization"]) == 0
    assert json.loads(capsys.readouterr().out)["candidates"][0]["id"] == "aide"
