from pathlib import Path
from pdrw_orchestrator.models import TaskPacket
from pdrw_orchestrator.controller import run_demo
from pdrw_orchestrator.planner import demo_plan
from pdrw_orchestrator.policy import load_policy
from pdrw_orchestrator.registry import load_agents

ROOT = Path(__file__).resolve().parents[1]
RULES = load_policy(ROOT / "policies/user/research-guidance.example.yaml")
AGENTS = load_agents(ROOT / "configs/agents.example.yaml")


def test_demo_two_agents_handoff_is_not_science():
    report = run_demo(demo_plan(), AGENTS, RULES)
    assert len(report.results) == 2
    assert all(x.status == "DEMO_ONLY" and x.scientific_verified is False for x in report.results)
    assert report.results[0].agent_id != report.results[1].agent_id
    assert report.handoffs[1]["dependency_results"][0]["task_id"] == "DEMO-1"
    assert report.to_dict()["scientific_gain_measured"] is False


def test_effect_task_fails_closed_and_blocks_dependents():
    tasks = (
        TaskPacket(task_id="T1", project_id="P", task_type="code_experiment",
                   objective="train", required_effects=("local_dev_execution",)),
        TaskPacket(task_id="T2", project_id="P", task_type="analysis",
                   objective="review", dependencies=("T1",)),
    )
    report = run_demo(tasks, AGENTS, RULES)
    assert [x.status for x in report.results] == ["BLOCKED_AUTH", "BLOCKED_DEPENDENCY"]


def test_not_connected_agent_never_advertises_readiness():
    task = TaskPacket(task_id="T", project_id="P", task_type="optimization", objective="opt")
    report = run_demo((task,), AGENTS, RULES)
    assert report.results[0].status == "NOT_CONNECTED"


def test_policy_denial_is_not_a_permit():
    task = TaskPacket(task_id="T", project_id="P", task_type="analysis",
                      objective="write", required_effects=("manuscript_write",))
    report = run_demo((task,), AGENTS, RULES)
    assert report.results[0].status == "BLOCKED_POLICY"
