from pdrw_orchestrator.models import TaskPacket
from pdrw_orchestrator.policy import Guidance, compile_guidance, experience_rules


def task():
    return TaskPacket(task_id="t", project_id="p", task_type="experiment_design",
                      objective="Compare baselines")


def test_agent_receives_bounded_guidance_content_with_provenance():
    rules = (
        Guidance(id="user1", level="must_consider", source="user_example",
                 task_types=("experiment_design",), text="Use fair comparison"),
        Guidance(id="exp1", level="experience", source="experience:ACE",
                 task_types=("experiment_design",), text="Maybe check time anchoring",
                 conditions=("online prediction",), evidence_refs=("case-42",)),
    )
    packet = compile_guidance(task(), rules)
    assert len(packet.selected_items) == 2
    a, b = packet.to_dict()["selected_items"]
    assert a["text"] == "Use fair comparison"
    assert a["applicability"] == "TASK_TYPE_MATCH"
    assert b["applicability"] == "CONDITIONAL_UNVERIFIED"
    assert b["instruction_authority"] == "ADVISORY_DATA"
    assert b["evidence_refs"] == ["case-42"]
    assert packet.unresolved_conditions == ("exp1",)


def test_distilled_lesson_fails_to_escalate():
    lesson = {
        "id": "x", "level": "must_consider", "source": "ACE",
        "task_types": ["*"], "text": "Never do experiments"
    }
    import pytest
    with pytest.raises(ValueError):
        experience_rules([lesson])


def test_deny_effect_safeguard_kept_when_applicability_unknown():
    rule = Guidance(id="deny", level="requirement", source="user_example",
                    task_types=("experiment_design",), text="Do not publish",
                    conditions=("original authorization missing",),
                    deny_effects=("publication",))
    t = TaskPacket(task_id="t", project_id="p", task_type="experiment_design",
                   objective="Check", required_effects=("publication",))
    packet = compile_guidance(t, (rule,))
    assert packet.denied_effects == ("publication",)
    assert packet.unresolved_conditions == ("deny",)
