"""Mechanical result checks only; real science review delegated to PD-RW host."""
from .models import ResultPacket, TaskPacket


def review_result(task: TaskPacket, result: ResultPacket) -> tuple[str, ...]:
    problems = []
    if result.task_id != task.task_id:
        problems.append("TASK_ID_MISMATCH")
    if result.scientific_verified:
        problems.append("UNSUPPORTED_SCIENCE_ATTESTATION")
    if result.status == "COMPLETED" and not result.output_refs:
        problems.append("MISSING_OUTPUT_REFS")
    return tuple(problems)
