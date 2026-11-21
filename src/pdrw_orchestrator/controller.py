"""One-attempt task DAG executor; dry-run only, no side effects."""
from __future__ import annotations
from dataclasses import dataclass

from .adapters.mock import MockAdapter
from .handoff import prepare_handoff
from .models import ResultPacket, TaskPacket
from .policy import Guidance, compile_guidance
from .registry import AgentSpec
from .review import review_result
from .router import route


def order_tasks(tasks: tuple[TaskPacket, ...]) -> tuple[TaskPacket, ...]:
    lookup = {task.task_id: task for task in tasks}
    if len(lookup) != len(tasks):
        raise ValueError("duplicate task id")
    if len({task.project_id for task in tasks}) > 1:
        raise ValueError("mixed project identities")
    if any(dep not in lookup for task in tasks for dep in task.dependencies):
        raise ValueError("missing dependency")
    ordered: list[TaskPacket] = []
    completed: set[str] = set()
    while len(ordered) < len(tasks):
        ready = sorted((t for t in tasks if t.task_id not in completed
                        and all(dep in completed for dep in t.dependencies)),
                       key=lambda t: t.task_id)
        if not ready:
            raise ValueError("cyclic dependencies")
        next_task = ready[0]
        ordered.append(next_task)
        completed.add(next_task.task_id)
    return tuple(ordered)


@dataclass(frozen=True)
class ExecutionReport:
    results: tuple[ResultPacket, ...]
    handoffs: tuple[dict, ...]

    def to_dict(self) -> dict:
        return {
            "mode": "MOCK_ONLY",
            "scientific_gain_measured": False,
            "results": [r.to_dict() for r in self.results],
            "handoffs": list(self.handoffs),
        }


def run_demo(tasks: tuple[TaskPacket, ...], agents: tuple[AgentSpec, ...],
             rules: tuple[Guidance, ...]) -> ExecutionReport:
    results: dict[str, ResultPacket] = {}
    handoffs: list[dict] = []
    for task in order_tasks(tasks):
        prior = tuple(results[dep] for dep in task.dependencies)
        guidance = compile_guidance(task, rules)
        handoffs.append(prepare_handoff(task, prior, guidance))
        if any(r.status not in ("DEMO_ONLY", "COMPLETED") for r in prior):
            result = ResultPacket(task_id=task.task_id, agent_id="controller",
                                  status="BLOCKED_DEPENDENCY", details="upstream task unavailable")
        elif guidance.denied_effects:
            result = ResultPacket(task_id=task.task_id, agent_id="controller",
                                  status="BLOCKED_POLICY", details="user guidance denied requested effect")
        elif task.required_effects:
            result = ResultPacket(task_id=task.task_id, agent_id="controller",
                                  status="BLOCKED_AUTH", details="no authenticated effect-granting host bridge")
        else:
            agent = route(task, agents)
            result = (MockAdapter().run(task, guidance, agent) if agent is not None
                      else ResultPacket(task_id=task.task_id, agent_id="controller",
                                        status="NOT_CONNECTED", details="no verified-ready adapter"))
        defects = review_result(task, result)
        if defects:
            result = ResultPacket(task_id=task.task_id, agent_id="controller",
                                  status="NEEDS_REVIEW", details=";".join(defects))
        results[task.task_id] = result
    return ExecutionReport(results=tuple(results[t.task_id] for t in order_tasks(tasks)),
                           handoffs=tuple(handoffs))
