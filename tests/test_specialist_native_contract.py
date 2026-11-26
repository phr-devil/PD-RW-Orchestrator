"""Real pinned upstream code, no live model or HTTP requests.

Ordinary CI skips these unless the source roots are explicitly configured.
The dedicated native-contract job fetches public source and test dependencies.
Only the HTTP transport is substituted; the native REST tool itself is not.
AIDE executes a fixed, human-written CPU fixture, not generated code/search.
"""
import csv
import json
import os
import shutil
import socket
import sys
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

import pytest

from pdrw_orchestrator import aide_pilot, specialist_host
from pdrw_orchestrator.adapters.aide_install import inspect_specialist_install
from pdrw_orchestrator.adapters import tooluniverse


def _source(var, monkeypatch):
    root = os.environ.get(var)
    if not root:
        pytest.skip("explicit upstream source root not configured")
    root = Path(root).resolve()
    assert root.is_dir()
    monkeypatch.syspath_prepend(str(root))
    return root


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("Network is not part of the native offline contract")
    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket.socket, "connect_ex", denied)
    monkeypatch.setattr(socket, "getaddrinfo", denied)


def test_native_aide_config_workspace_and_fixed_code(tmp_path, monkeypatch):
    source = _source("PDRW_NATIVE_AIDE_ROOT", monkeypatch)
    assert inspect_specialist_install("aide", source)["status"] == "PINNED_SELECTED_BYTES_MATCH"
    from aide.utils.config import load_cfg, load_task_desc, prep_agent_workspace
    from aide.interpreter import Interpreter

    root = tmp_path.resolve() / "pilot"
    pilot = aide_pilot.prepare(root, attempt_id="true", code_provider="openai",
                              code_model="null", feedback_provider="anthropic",
                              feedback_model="fixture-feedback", steps=1, step_timeout_seconds=20)
    monkeypatch.chdir(root / "worker")
    monkeypatch.setattr(sys, "argv", pilot["argv_preview"])
    cfg = load_cfg()
    assert cfg.exp_name == "0-true"
    assert cfg.agent.code.model == "null"
    assert cfg.agent.feedback.provider == "anthropic"
    assert cfg.agent.steps == 1 and cfg.agent.metric_maximize is False
    assert cfg.agent.data_preview is False and cfg.agent.k_fold_validation == 1
    assert cfg.generate_report is False and cfg.preprocess_data is False and cfg.copy_data is True
    assert load_task_desc(cfg) == (root / "worker" / "task.md").read_text(encoding="utf-8")
    prep_agent_workspace(cfg)
    assert {p.name for p in (cfg.workspace_dir / "input").iterdir()} == {"train.csv","validation.csv","test.csv"}
    for path in (cfg.workspace_dir / "input").iterdir():
        assert path.read_bytes() == (root / "worker" / "data" / path.name).read_bytes()
        assert not path.is_symlink()
    # Human-written constant predictor; no model calls, fitting or training.
    code = """import csv
from pathlib import Path
with Path("input/test.csv").open(newline="") as f:
    ids = [row["row_id"] for row in csv.DictReader(f)]
with Path("working/submission.csv").open("w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["row_id", "prediction"])
    writer.writerows((row_id, 0) for row_id in ids)
print("FIXED_NATIVE_PREDICTOR_OK", len(ids))
"""
    interpreter = Interpreter(cfg.workspace_dir, timeout=cfg.exec.timeout)
    try:
        result = interpreter.run(code)
        assert result.exc_type is None
        assert "FIXED_NATIVE_PREDICTOR_OK" in "".join(result.term_out)
    finally:
        interpreter.cleanup_session()
    shutil.copyfile(cfg.workspace_dir / "working/submission.csv", root / "review/submission.csv")
    score = aide_pilot.score(root)
    assert score["rows"] == 48 and score["independent_group_count"] == 4
    assert score["candidate_rmse"] > score["linear_baseline_rmse"]
    assert not score["scientific_validity_verified"]
    print("NATIVE_AIDE_FIXED_CODE_ONLY", json.dumps({
        "rows":score["rows"], "groups":score["independent_group_count"],
        "candidate_rmse":score["candidate_rmse"], "linear_baseline_rmse":score["linear_baseline_rmse"],
        "model_calls":0, "autonomous_search_tested":False}))


@pytest.mark.parametrize("operation", ["search","doi","dataset"])
def test_native_tooluniverse_rest_transport(tmp_path, monkeypatch, operation):
    source = _source("PDRW_NATIVE_TU_ROOT", monkeypatch)
    assert inspect_specialist_install("tooluniverse",source)["status"] == "PINNED_SELECTED_BYTES_MATCH"
    monkeypatch.setenv("TOOLUNIVERSE_LIGHT_IMPORT","true")
    import requests
    from tooluniverse import current_credentials

    calls = []
    doi = "10.1234/example"
    paper = {"DOI":doi,"title":["Synthetic interface fixture"],"published":{"date-parts":[[2025]]}}
    def intercepted(session, request, **kwargs):
        url = urlsplit(request.url)
        params = parse_qs(url.query)
        calls.append((url.hostname, url.path))
        assert session.trust_env is False
        assert current_credentials() == {}
        assert "Authorization" not in request.headers
        assert request.method == "GET"
        if operation == "dataset":
            assert url.hostname == "zenodo.org" and url.path == "/api/records"
            assert params["size"] == ["2"]
            assert params["page"] == ["1"]
            assert params["q"] == ["resource_type.type:dataset AND (public sensor fixture)"]
            body = {"hits":{"total":1,"hits":[{"id":10,"doi":"10.5281/zenodo.10",
                    "metadata":{"title":"Synthetic dataset metadata","resource_type":{"type":"dataset"},
                                "license":{"id":"cc-by-4.0"}}}]}}
        else:
            assert url.hostname == "api.crossref.org"
            if operation == "doi":
                assert unquote(url.path) == "/works/" + doi
                body = {"message":paper}
            else:
                assert url.path == "/works" and params["rows"] == ["2"]
                assert params["query"] == ["public sensor fixture"]
                body = {"message":{"items":[paper],"total-results":100}}
        response = requests.Response()
        response.status_code = 200
        response.headers["Content-Type"] = "application/json"
        response._content = json.dumps(body).encode("utf-8")
        response.url = request.url
        response.request = request
        return response
    monkeypatch.setattr(requests.Session,"send",intercepted)
    plan = {"schema_version":"tooluniverse-public-dataset-v1" if operation == "dataset" else "tooluniverse-public-literature-v1",
            "project_id":"PUBLIC-EXAMPLE","task_id":"T","attempt_id":"native-1","operation":operation,
            "public_text":doi if operation == "doi" else "public sensor fixture",
            "limit":1 if operation == "doi" else 2}
    root = tmp_path.resolve() / "lookup"
    packet = tooluniverse.query(plan,root,source,execute=True,ack_public_network=True)
    assert len(calls) == 1
    assert specialist_host.verify_artifacts(packet,root)["artifact_bytes_reverified"]
    summary = specialist_host.review_metadata(packet)["provider_summary"]
    assert summary["candidate_count"] == 1 and not summary["literature_verified"]
    if operation == "search":
        assert summary["total_count_reported"] == 100
    if operation == "dataset":
        assert not summary["license_verified"]
    print("NATIVE_TOOLUNIVERSE_INTERCEPTED_HTTP_ONLY", operation, "candidate_count=1")
