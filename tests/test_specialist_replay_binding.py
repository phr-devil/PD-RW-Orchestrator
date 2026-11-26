import csv

from pdrw_orchestrator import specialist_host, aide_pilot
from pdrw_orchestrator.adapters import rdagent


def test_rd_original_and_replay_predictions_distinct(tmp_path):
    root = tmp_path.resolve() / "rd"
    rdagent.prepare(root, attempt_id="rd1", config_sha256="a"*64)
    export = root / "review" / "candidate"
    export.mkdir()
    (export/"main.py").write_text("pass", encoding="utf-8")
    (export/"scores.csv").write_text("native score",encoding="utf-8")
    (export/"submission.csv").write_text("original provider predictions, not replay",encoding="utf-8")
    ids = [key for key,(group,x,y) in aide_pilot._rows().items() if int(group[1:]) >= 8]
    with (root/"review"/"submission.csv").open("w",newline="",encoding="ascii") as stream:
        writer = csv.writer(stream)
        writer.writerow(["row_id","prediction"])
        writer.writerows((key,0) for key in ids)
    packet = specialist_host.collect("rdagent",root,score_replay=True)
    files = {a["ref"]:a["sha256"] for a in packet["artifact_observation"]["artifacts"]}
    assert files["review/submission.csv"] != files["review/candidate/submission.csv"]
    assert files["review/submission.csv"] == packet["artifact_observation"]["provider_summary"]["prediction_sha256"]
    assert specialist_host.verify_artifacts(packet,root)["artifact_bytes_reverified"]
