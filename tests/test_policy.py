from pathlib import Path
import pytest

from pdrw_orchestrator.models import TaskPacket
from pdrw_orchestrator.policy import Guidance, compile_guidance, experience_rules, load_policy

ROOT = Path(__file__).resolve().parents[1]


def task(**kwargs):
    return TaskPacket(task_id="t", project_id="p", task_type="experiment_design",
                      objective="o", **kwargs)


def test_example_policy_applies_only_to_relevant_tasks():
    rules = load_policy(ROOT / "policies/user/research-guidance.example.yaml")
    compiled = compile_guidance(task(), rules)
    assert "ALG-BASELINE" in compiled.must_consider
    assert "ALG-IMPORTANCE" not in compiled.rule_ids
    assert compiled.to_dict()["permission_granted"] is False


def test_user_effect_restriction_and_auth_separate():
    rules = load_policy(ROOT / "policies/user/research-guidance.example.yaml")
    t = task(required_effects=("manuscript_write",))
    assert "manuscript_write" in compile_guidance(t, rules).denied_effects


def test_experience_cannot_escalate_to_requirement():
    with pytest.raises(ValueError):
        experience_rules([{
            "id": "lesson", "level": "requirement", "source": "llm",
            "task_types": ["*"], "text": "do X",
        }])
    with pytest.raises(ValueError):
        Guidance.from_dict({
            "id": "lesson", "level": "experience", "source": "experience:abc",
            "task_types": ["*"], "text": "do X", "deny_effects": ["upload"],
        })


def test_duplicate_ids_cannot_override():
    r = Guidance(id="x", level="recommendation", source="user", task_types=("*",), text="x")
    with pytest.raises(ValueError):
        compile_guidance(task(), (r, r))
