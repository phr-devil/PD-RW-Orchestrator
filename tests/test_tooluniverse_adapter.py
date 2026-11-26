import json
import pytest

from pdrw_orchestrator.adapters import tooluniverse
from pdrw_orchestrator.cli import main
from pdrw_orchestrator.policy import Guidance
from pdrw_orchestrator.specialist_host import unpack_intake, review_metadata
from pdrw_orchestrator.specialists import recommend
from pdrw_orchestrator.models import TaskPacket


def plan():
    return {"schema_version":"tooluniverse-public-literature-v1", "project_id":"P", "task_id":"T",
            "attempt_id":"a1", "operation":"search", "public_text":"public sensor research", "limit":2}


def response():
    return {"status":"success", "count":2, "total_count":100,
            "data":[{"DOI":"10.1234/example", "title":["Example"], "container-title":["Journal"],
                     "published":{"date-parts":[[2025]]}, "is-referenced-by-count":3},
                    {"DOI":"10.1234/example", "title":["Duplicate"]}]}


def test_native_call_opt_in_and_intake(tmp_path, monkeypatch, capsys):
    calls = []
    def fake(call, source_root):
        calls.append(call)
        return response()
    monkeypatch.setattr(tooluniverse, "_native_call", fake)
    p = plan()
    root = tmp_path.resolve() / "lookup"
    with pytest.raises(ValueError, match="OPT_IN"):
        tooluniverse.query(p, root, "unused")
    assert not root.exists() and not calls
    packet = tooluniverse.query(p, root, "unused", execute=True, ack_public_network=True)
    assert len(calls) == 1 and calls[0]["name"] == "Crossref_search_works"
    task, raw = unpack_intake(packet)
    assert task.capability == "literature_lookup"
    assert not raw["scientific_completion_verified"]
    summary = review_metadata(packet)["provider_summary"]
    assert summary["candidate_count"] == 1 and summary["total_count_reported"] == 100
    assert not summary["literature_verified"]
    assert packet == tooluniverse.collect(p, root)
    with pytest.raises(ValueError):
        tooluniverse.query(p, root, "unused", execute=True, ack_public_network=True)
    assert len(calls) == 1
    path = tmp_path / "intake.json"
    path.write_text(json.dumps(packet), encoding="utf-8")
    assert main(["advise", "--intake-file", str(path)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["decision"]["decision_type"] == "INDEPENDENT_REVIEW"
    assert not result["scientific_completion_verified"]


def test_policy_denial_before_network(tmp_path, monkeypatch):
    def never(*args):
        pytest.fail("network call must be blocked")
    monkeypatch.setattr(tooluniverse, "_native_call", never)
    deny = Guidance.from_dict({"id":"N","level":"requirement","source":"user","task_types":["*"],
                               "text":"deny network","deny_effects":["network"]})
    with pytest.raises(ValueError, match="POLICY_DENIED"):
        tooluniverse.query(plan(), tmp_path.resolve()/"new", "unused", execute=True, ack_public_network=True, rules=(deny,))


@pytest.mark.parametrize("change",[{"limit":21},{"operation":"arbitrary"},{"public_text":"\nsecret"},
                                   {"limit":True},{"operation":"doi","public_text":"bad","limit":1}])
def test_bad_plan(change):
    with pytest.raises(ValueError):
        tooluniverse.preview(dict(plan(), **change))


def test_native_doi_binding():
    p = dict(plan(), operation="doi", public_text="10.1234/example", limit=1)
    assert tooluniverse.preview(p)["native_call"]["name"] == "Crossref_get_work"
    good = tooluniverse._metadata({"status":"success","data":{"DOI":"10.1234/EXAMPLE"}}, p)
    assert good["unique_candidate_count"] == 1
    with pytest.raises(ValueError, match="DOI_RESPONSE_MISMATCH"):
        tooluniverse._metadata({"status":"success","data":{"DOI":"10.1234/wrong"}}, p)


def test_zero_model_budget_routes_to_public_metadata():
    task = TaskPacket(task_id="T", project_id="P", task_type="discovery", capability="doi_lookup",
                      objective="Find metadata", budget={"max_model_calls":0})
    route = recommend(task, scope="public_topic")
    assert route["recommended_candidate"] == "tooluniverse"
    assert not route["can_auto_dispatch"]
