import pytest

from pdrw_orchestrator.models import ResultPacket, TaskPacket
from pdrw_orchestrator.controller import order_tasks


def test_task_result_contract_rejects_missing_identity():
    with pytest.raises(ValueError):
        TaskPacket(task_id="", project_id="P1", task_type="discovery", objective="x")
    with pytest.raises(ValueError):
        ResultPacket(task_id="A", agent_id="mock", status="VALID_POS", details="fake")


def test_dag_order_and_missing_dependency():
    tasks = (
        TaskPacket(task_id="B", project_id="P1", task_type="analysis", objective="b", dependencies=("A",)),
        TaskPacket(task_id="A", project_id="P1", task_type="discovery", objective="a"),
    )
    assert [t.task_id for t in order_tasks(tasks)] == ["A", "B"]
    with pytest.raises(ValueError):
        order_tasks((tasks[0],))
    with pytest.raises(ValueError):
        order_tasks((
            TaskPacket(task_id="A", project_id="P1", task_type="discovery", objective="a", dependencies=("B",)),
            tasks[0],
        ))
