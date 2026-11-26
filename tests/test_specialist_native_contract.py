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


def test_native_rd_settings_and_cli_source_contract(tmp_path, monkeypatch):
    import ast
    from pdrw_orchestrator.adapters import rdagent
    source = _source("PDRW_NATIVE_RD_ROOT", monkeypatch)
    assert inspect_specialist_install("rdagent", source)["status"] == "PINNED_SELECTED_BYTES_MATCH"
    root = tmp_path.resolve() / "rd"
    pilot = rdagent.prepare(root, attempt_id="native-rd", config_sha256="a"*64)
    monkeypatch.chdir(root / "worker")
    # Native Pydantic settings inherit KG_ values; conflicting inherited settings
    # must not defeat explicit DS_ overrides.
    monkeypatch.setenv("KG_AUTO_SUBMIT", "true")
    monkeypatch.setenv("KG_IF_USING_MLE_DATA", "true")
    monkeypatch.setenv("KG_IF_USING_GRAPH_RAG", "true")
    for key, value in pilot["environment_preview"].items():
        monkeypatch.setenv(key, value)
    from rdagent.app.data_science.conf import DataScienceBasePropSetting
    settings = DataScienceBasePropSetting()
    assert settings.scen.endswith(".DataScienceScen")
    assert Path(settings.local_data_path) == root / "worker" / "ds_data"
    assert not settings.auto_submit and not settings.if_using_mle_data
    assert not settings.if_using_graph_rag and not settings.if_using_vector_rag
    assert not settings.sample_data_by_LLM and not settings.enable_log_archive
    assert not settings.enable_knowledge_base and not settings.enable_research_rag
    assert settings.eval_sub_dir == "eval"
    assert settings.debug_timeout == 120 and settings.full_timeout == 120
    assert settings.coder_max_loop == 2 and settings.runner_max_loop == 1
    # The full CLI imports unrelated research stacks; inspect its original
    # command declaration rather than pretending those dependencies ran.
    tree = ast.parse((source / "rdagent/app/cli.py").read_text(encoding="utf-8"))
    func = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                and node.name == "data_science_cli")
    names = {arg.arg for arg in func.args.args}
    assert {"competition","checkout","loop_n","step_n","timeout"} <= names
    assert "--no-checkout" in (source / "rdagent/app/cli.py").read_text(encoding="utf-8")
    argv = pilot["argv_preview"]
    competition = argv[argv.index("--competition")+1]
    assert (Path(settings.local_data_path)/competition/"description.md").is_file()
    assert (Path(settings.local_data_path)/"sample"/competition/"description.md").is_file()
    assert not (Path(settings.local_data_path)/settings.eval_sub_dir/competition/"submission_test.csv").exists()
    print("NATIVE_RD_SETTINGS_ONLY", "custom_scenario=true", "auto_submit=false", "full_cli_executed=false")


def test_native_arc_parser_config_and_stage_contract(tmp_path, monkeypatch):
    import hashlib
    from pdrw_orchestrator.adapters.arc import preview_arc, discovery_config_issues
    source = _source("PDRW_NATIVE_ARC_ROOT", monkeypatch)
    assert inspect_specialist_install("arc", source)["status"] == "PINNED_SELECTED_BYTES_MATCH"
    from researchclaw.cli import build_parser
    from researchclaw.config import RCConfig
    from researchclaw.pipeline.stages import Stage, STAGE_SEQUENCE
    raw = (Path(__file__).resolve().parents[1] / "examples/arc-discovery.config.example.yaml").read_bytes()
    assert not discovery_config_issues(raw, 10)
    plan = {"schema_version":"arc-discovery-preview-v1","project_id":"PUBLIC-EXAMPLE",
            "task_id":"T","attempt_id":"native-arc","public_topic":"public sensor fixture",
            "research_scope":"literature only","max_papers":10,
            "config_sha256":hashlib.sha256(raw).hexdigest()}
    config_file = tmp_path / "config.arc.yaml"
    config_file.write_bytes(raw)
    monkeypatch.chdir(tmp_path)
    args = build_parser().parse_args(preview_arc(plan)["argv_preview"][1:])
    assert args.command == "run" and not args.auto_approve and not args.resume
    assert args.no_graceful_degradation and args.output == "run"
    assert args.config == "config.arc.yaml"
    cfg = RCConfig.load(config_file, check_paths=False)
    assert cfg.project.mode == "semi-auto" and cfg.experiment.mode == "simulated"
    assert not cfg.memory.enabled and not cfg.skills.enabled
    assert not cfg.security.allow_publish_without_approval and not cfg.web_search.enabled
    assert not cfg.metaclaw_bridge.enabled and not cfg.overleaf.enabled
    assert cfg.knowledge_base.root == "kb"
    assert cfg.literature_search.max_results_per_query == 10
    stages = [s for s in STAGE_SEQUENCE if Stage[args.from_stage] <= s <= Stage[args.to_stage]]
    assert stages == [Stage.TOPIC_INIT, Stage.PROBLEM_DECOMPOSE, Stage.SEARCH_STRATEGY, Stage.LITERATURE_COLLECT]
    print("NATIVE_ARC_PARSER_CONFIG_ONLY", "stages=1-4", "pipeline_executed=false")
