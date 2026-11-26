import hashlib
import json
import pytest

from pdrw_orchestrator.adapters import aide_install
from pdrw_orchestrator.adapters.arc import preview_arc, collect_arc, _FILES
from pdrw_orchestrator.cli import main
from pdrw_orchestrator.agent_result import normalize_result
from pdrw_orchestrator.models import TaskPacket


def plan():
    return {"schema_version": "arc-discovery-preview-v1", "project_id": "P", "task_id": "T",
            "attempt_id": "a1", "public_topic": "Public synthetic sensor research",
            "research_scope": "Literature candidates only", "max_papers": 10, "config_sha256": "a"*64}


def test_source_subset_match_and_tamper(tmp_path, monkeypatch):
    root = tmp_path.resolve()
    raw = b"test source\n"
    expected = hashlib.sha1(b"blob 12\0" + raw).hexdigest()
    assert aide_install._git_blob(raw) == expected
    monkeypatch.setattr(aide_install, "_BLOBS", {"aide/run.py": expected})
    (root / "aide").mkdir()
    p = root / "aide" / "run.py"
    p.write_bytes(raw)
    checked = aide_install.inspect_aide_install(root)
    assert checked["status"] == "PINNED_SELECTED_BYTES_MATCH"
    assert not checked["capability_accepted"]
    p.write_bytes(b"changed")
    assert aide_install.inspect_aide_install(root)["status"] == "PINNED_SELECTED_BYTES_NOT_MATCHED"
    p.unlink()
    assert aide_install.inspect_aide_install(root)["files"][0]["status"] == "UNAVAILABLE_OR_UNSAFE"


def test_preview_caps_native_scope():
    value = preview_arc(plan())
    args = value["argv_preview"]
    assert args[args.index("--to-stage")+1] == "LITERATURE_COLLECT"
    assert "--auto-approve" not in args
    assert "--resume" not in args
    assert not value["execution_authorized"]
    assert not value["hard_budget_enforced"]
    assert value == preview_arc(dict(reversed(list(plan().items()))))


@pytest.mark.parametrize("change", [{"public_topic": "--resume"}, {"max_papers": 31},
    {"config_sha256": "wrong"}, {"attempt_id": "../bad"}, {"to_stage": "PAPER_DRAFT"}])
def test_preview_rejects_invalid(change):
    with pytest.raises(ValueError):
        preview_arc(dict(plan(), **change))


def fixture(root):
    for ref in _FILES:
        path = root / ref
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("observed", encoding="utf-8")
    (root / "pipeline_summary.json").write_text(json.dumps({
        "from_stage": 1, "final_stage": 4, "stages_executed": 4, "stages_done": 4,
        "stages_failed": 0, "stages_blocked": 0, "stages_paused": 0,
        "final_status": "done", "degraded": False}), encoding="utf-8")
    (root / "stage-04/candidates.jsonl").write_text('{"is_placeholder":true}\n{"title":"unverified"}\n', encoding="utf-8")
    (root / "stage-04/search_meta.json").write_text('{"real_search":false,"total_candidates":2}', encoding="utf-8")


def test_intake_and_normalization(tmp_path):
    root = tmp_path.resolve()
    fixture(root)
    value = collect_arc(plan(), root)
    assert value["candidate_count"] == 2 and value["declared_placeholder_count"] == 1
    assert not value["real_search_reported"] and not value["literature_verified"]
    raw = value["agent_result"]
    normalized = normalize_result(raw, TaskPacket(task_id="T", project_id="P", task_type="discovery", objective="Review"))
    assert normalized["execution"]["reported_status"] == "NEEDS_REVIEW"
    assert not normalized["scientific_completion_verified"]
    (root / "stage-05").mkdir()
    with pytest.raises(ValueError):
        collect_arc(plan(), root)


def test_incomplete_and_count_mismatch(tmp_path):
    root = tmp_path.resolve()
    fixture(root)
    (root / "stage-04/search_meta.json").write_text('{"total_candidates":3}', encoding="utf-8")
    with pytest.raises(ValueError):
        collect_arc(plan(), root)
    fixture(root)
    (root / "pipeline_summary.json").write_text('{"final_stage":4}', encoding="utf-8")
    with pytest.raises(ValueError):
        collect_arc(plan(), root)


def test_cli(tmp_path, capsys):
    p = tmp_path / "plan.json"
    p.write_text(json.dumps(plan()), encoding="utf-8")
    assert main(["arc", "preview", "--plan-file", str(p)]) == 0
    assert json.loads(capsys.readouterr().out)["stage_ceiling"] == 4
