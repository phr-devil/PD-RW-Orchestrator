import hashlib
import json

import pytest

from pdrw_orchestrator.adapters import rdagent
from pdrw_orchestrator import specialist_host, specialist_plan
from pdrw_orchestrator.models import TaskPacket
from pdrw_orchestrator.cli import main


def fixture(root):
    raw = b"x,y\n1,2\n"
    for name in ("pdrw-dev-task", "sample/pdrw-dev-task"):
        path = root / "worker" / "ds_data" / name
        path.mkdir(parents=True)
        (path / "train.csv").write_bytes(raw)
    (root / "review").mkdir()
    manifest = {"schema_version": "aide-dev-snapshot-v1", "project_id": "P", "task_id": "D",
                "scope": "DEV_ONLY_DECLARED",
                "files": [{"name": "train.csv", "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}]}
    data = json.dumps(manifest).encode()
    (root / "review" / "manifest.json").write_bytes(data)
    return {"schema_version": "rdagent-dev-preview-v1", "project_id": "P", "task_id": "D",
            "attempt_id": "rd1", "goal": "Candidate regression", "evaluation": "Fixed grouped DEV",
            "protocol_ref": "P/PROTO", "data_manifest_sha256": hashlib.sha256(data).hexdigest(),
            "loops": 1, "steps": 5, "timeout_seconds": 600, "provider_config_sha256_declared": "a"*64}


def test_custom_stage_collect_and_compile(tmp_path, capsys):
    root = tmp_path.resolve() / "rd"
    plan = fixture(root)
    task = TaskPacket(project_id="P", task_id="D", task_type="code_experiment",
                      capability="research_iteration", objective="Develop", protocol_refs=("P/PROTO",))
    options = {k:v for k,v in plan.items() if k not in ("schema_version", "project_id", "task_id")}
    compiled = specialist_plan.compile_plan(task, "staged_dev", options)
    assert compiled["native_plan"] == plan
    assert compiled["route"]["recommended_candidate"] == "rdagent"
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(plan), encoding="utf-8")
    assert main(["rdagent-dev","stage","--root",str(root),"--plan-file",str(path)]) == 0
    value = json.loads(capsys.readouterr().out)
    assert value["status"] == "RDAGENT_DECLARED_DEV_SNAPSHOT_BYTES_MATCH_ONLY"
    assert "pdrw-dev-task" in value["argv_preview"]
    assert value["environment_preview"]["DS_EVAL_SUB_DIR"] == "eval"
    assert not value["actual_data_scope_verified"]
    handoff = specialist_host.prepare("rdagent",root,plan=plan)
    assert handoff["task"]["project_id"] == "P"
    assert handoff["task"]["capability"] == "research_iteration"
    assert not handoff["execution_authorized"]
    export = root / "review" / "candidate"
    export.mkdir()
    for name in ("main.py","scores.csv","submission.csv"):
        (export / name).write_text("fixture", encoding="utf-8")
    packet = specialist_host.collect("rdagent",root,plan=plan)
    assert packet["task"]["task_id"] == "D"
    assert specialist_host.verify_artifacts(packet,root)["artifact_bytes_reverified"]
    with pytest.raises(ValueError):
        specialist_host.collect("rdagent",root,plan=plan,score_replay=True)


def test_custom_dev_rejects_eval_and_mutation(tmp_path):
    root = tmp_path.resolve() / "rd"
    plan = fixture(root)
    forbidden = root / "worker" / "ds_data" / "eval"
    forbidden.mkdir()
    with pytest.raises(ValueError,match="TREE_MISMATCH"):
        rdagent.stage_dev(root,plan)
    forbidden.rmdir()
    rdagent.stage_dev(root,plan)
    (root/"worker"/"ds_data"/"sample"/"pdrw-dev-task"/"train.csv").write_bytes(b"x,y\n1,9\n")
    with pytest.raises(ValueError,match="BYTES_MISMATCH"):
        rdagent.verify_dev(root,plan)
