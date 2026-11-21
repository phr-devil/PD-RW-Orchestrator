"""Minimal evidence-reference handoff, not a science ledger."""
from .models import ResultPacket, TaskPacket
from .policy import GuidancePacket


def prepare_handoff(task: TaskPacket, earlier: tuple[ResultPacket, ...],
                    guidance: GuidancePacket) -> dict:
    if any(result.task_id not in task.dependencies for result in earlier):
        raise ValueError("handoff contains an unrelated task")
    return {
        "schema_version": "1.0",
        "task_id": task.task_id,
        "project_id": task.project_id,
        "dependency_results": [result.to_dict() for result in earlier],
        "evidence_refs": list(task.evidence_refs),
        "protocol_refs": list(task.protocol_refs),
        "authorization_refs": list(task.authorization_refs),
        "guidance": guidance.to_dict(),
        "original_authorization_authenticated": False,
        "scientific_claim_verified": False,
    }
