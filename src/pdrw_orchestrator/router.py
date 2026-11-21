"""Deterministic, fail-closed capability routing."""
from .models import TaskPacket
from .registry import AgentSpec


def route(task: TaskPacket, agents: tuple[AgentSpec, ...]) -> AgentSpec | None:
    capability = task.capability or task.task_type
    candidates = [a for a in agents if capability in a.capabilities and a.verified_ready]
    return min(candidates, key=lambda a: (a.priority, a.id)) if candidates else None
