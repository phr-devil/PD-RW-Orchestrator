import json
import pytest

from pdrw_orchestrator.adapters import tooluniverse
from pdrw_orchestrator import specialist_plan, specialist_host
from pdrw_orchestrator.models import TaskPacket
from pdrw_orchestrator.specialists import recommend


def plan():
    return {"schema_version":"tooluniverse-public-dataset-v1","project_id":"P",
            "task_id":"D","attempt_id":"a1","operation":"dataset",
            "public_text":"wearable sensors","limit":3}


def test_dataset_metadata_only(tmp_path, monkeypatch):
    seen = []
    def fake(call, source_root):
        seen.append(call)
        return {"status":"success","count":3,"data":{"hits":{"total":{"value":100,"relation":"eq"},
            "hits":[{"id":10,"doi":"10.5281/zenodo.10","metadata":{"resource_type":{"type":"dataset"},
                      "title":"Sensor dataset","license":{"id":"cc-by-4.0"},"access_right":"open","version":"v1"},
                      "files":[{"key":"private.csv","links":{"download":"https://example.invalid/private"}}]},
                    {"id":10,"metadata":{"resource_type":{"type":"dataset"}}},
                    {"id":11,"metadata":{"resource_type":{"type":"publication"}}}]}}}
    monkeypatch.setattr(tooluniverse,"_native_call",fake)
    root = tmp_path.resolve() / "zenodo"
    packet = tooluniverse.query(plan(),root,"unused",execute=True,ack_public_network=True)
    assert seen[0]["name"] == "Zenodo_search_records"
    assert seen[0]["arguments"]["query"].startswith("resource_type.type:dataset AND (")
    assert len(seen) == 1
    record = json.loads((root/"datasets.json").read_text())
    assert record["metadata"]["datasets"][0]["license_id_reported"] == "cc-by-4.0"
    assert "private.csv" not in json.dumps(record)
    assert record["metadata"]["unique_candidate_count"] == 1
    assert not record["metadata"]["data_downloaded"]
    task, raw = specialist_host.unpack_intake(packet)
    assert task.capability == "dataset_lookup"
    assert raw["deliverables"]["report_refs"] == ["datasets.json"]
    summary = specialist_host.review_metadata(packet)["provider_summary"]
    assert summary["record_kind"] == "dataset"
    assert not summary["license_verified"]
    assert specialist_host.verify_artifacts(packet,root)["artifact_bytes_reverified"]


def test_dataset_compile():
    task = TaskPacket(project_id="P",task_id="D",task_type="discovery",
                      capability="dataset_lookup",objective="Find public dataset candidates",
                      budget={"max_model_calls":0})
    assert recommend(task,scope="public_topic")["recommended_candidate"] == "tooluniverse"
    options = {k:v for k,v in plan().items() if k not in ("schema_version","project_id","task_id")}
    compiled = specialist_plan.compile_plan(task,"public_topic",options)
    assert compiled["native_plan"] == plan()
    assert not compiled["execution_authorized"]
    with pytest.raises(ValueError):
        tooluniverse.preview(dict(plan(),schema_version="tooluniverse-public-literature-v1"))
