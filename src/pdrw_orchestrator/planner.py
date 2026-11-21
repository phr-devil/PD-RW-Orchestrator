"""Explicit bounded DAG fixtures. A future host planner must use same contract."""
from .models import TaskPacket


def demo_plan(project_id: str = "DEMO") -> tuple[TaskPacket, ...]:
    return (
        TaskPacket(task_id="DEMO-1", project_id=project_id, task_type="discovery",
                   objective="Synthetic discovery demonstration; not a scientific search"),
        TaskPacket(task_id="DEMO-2", project_id=project_id, task_type="analysis",
                   objective="Synthetic downstream handoff; not a scientific analysis",
                   dependencies=("DEMO-1",)),
    )
