import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, RefResolver, validate

from pdrw_orchestrator.controller import run_demo
from pdrw_orchestrator.models import TaskPacket
from pdrw_orchestrator.planner import demo_plan
from pdrw_orchestrator.policy import load_policy
from pdrw_orchestrator.registry import load_agents

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas"


def schema(name):
    return json.loads((SCHEMAS / name).read_text(encoding="utf-8"))


def portable(value):
    return json.loads(json.dumps(value))


def test_schema_shapes_and_budget_match_runtime():
    task = TaskPacket(task_id="T", project_id="P", task_type="discovery",
                      objective="demo", budget={"max_model_calls": 0},
                      idempotency_key="demo-T")
    validate(instance=portable(task.to_dict()), schema=schema("task.schema.json"))
    with pytest.raises(ValueError):
        TaskPacket(task_id="T", project_id="P", task_type="discovery",
                   objective="demo", budget={"max_attempts": 0})


def test_handoff_and_registry_contracts():
    rules = load_policy(ROOT / "policies/user/research-guidance.example.yaml")
    agents = load_agents(ROOT / "configs/agents.example.yaml")
    report = run_demo(demo_plan(), agents, rules)
    ref = RefResolver(base_uri=SCHEMAS.as_uri() + "/", referrer=schema("handoff.schema.json"))
    for handoff in report.handoffs:
        Draft202012Validator(schema("handoff.schema.json"), resolver=ref).validate(portable(handoff))
    for agent in agents:
        validate(instance={
            "id": agent.id, "adapter": agent.adapter,
            "capabilities": list(agent.capabilities),
            "ready": agent.ready, "priority": agent.priority
        }, schema=schema("agent.schema.json"))
    for result in report.results:
        validate(instance=portable(result.to_dict()), schema=schema("result.schema.json"))
