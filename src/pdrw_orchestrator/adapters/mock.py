"""In-process no-effects adapter. Never represents real science."""
from pdrw_orchestrator.models import ResultPacket, TaskPacket
from pdrw_orchestrator.policy import GuidancePacket
from pdrw_orchestrator.registry import AgentSpec


class MockAdapter:
    def run(self, task: TaskPacket, guidance: GuidancePacket, agent: AgentSpec) -> ResultPacket:
        if task.required_effects:
            return ResultPacket(task_id=task.task_id, agent_id=agent.id, status="BLOCKED_AUTH",
                                details="mock adapter refuses effects")
        return ResultPacket(
            task_id=task.task_id, agent_id=agent.id, status="DEMO_ONLY",
            details=f"Simulated {task.task_type}; applied guidance IDs: {', '.join(guidance.rule_ids)}. No science performed.",
        )
