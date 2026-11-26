import json

from pdrw_orchestrator.adapters import tooluniverse
from pdrw_orchestrator.cli import main
from pdrw_orchestrator.specialist_host import scientific_review_focus


def test_provider_focus_distinguishes_tasks():
    assert "H4" in scientific_review_focus({"provider": "tooluniverse", "provider_summary": {"record_kind":"dataset"}})
    assert "placeholder" in scientific_review_focus({"provider":"arc","provider_summary":{"declared_placeholder_count":1}})
    assert "closest original papers" in scientific_review_focus({"provider":"tooluniverse"})
    for provider in ("aide","rdagent"):
        text = scientific_review_focus({"provider":provider})
        assert "valid negative" in text and "nearest work" in text


def test_existing_advice_contains_focus_without_new_task(tmp_path, monkeypatch, capsys):
    plan = {"schema_version":"tooluniverse-public-literature-v1","project_id":"P",
            "task_id":"T","attempt_id":"a1","operation":"search","public_text":"public topic","limit":2}
    monkeypatch.setattr(tooluniverse, "_native_call", lambda *args:{
        "status":"success","count":1,"data":[{"DOI":"10.1234/example","title":["Example"]}]})
    root = tmp_path.resolve() / "query"
    packet = tooluniverse.query(plan,root,"unused",execute=True,ack_public_network=True)
    path = tmp_path / "intake.json"
    path.write_text(json.dumps(packet),encoding="utf-8")
    assert main(["advise","--intake-file",str(path),"--intake-root",str(root)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["decision"]["decision_type"] == "INDEPENDENT_REVIEW"
    assert result["specialist_review_focus"] in result["agent_instruction_draft"]
    assert result["specialist_review_focus"] in result["chatgpt_handoff_md"]
    assert not result["scientific_completion_verified"]
    assert not result["dispatch_performed"]
