"""In-process host review boundary. NEVER an agent-owned JSON attestation.

The host implementation must check original PD-RW project identity, original
operation receipts and the referenced artifacts. This module contains no live
host implementation and does not authorize dispatch.
"""
from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Protocol

_SHA = re.compile(r"[0-9a-f]{64}\Z")

@dataclass(frozen=True)
class DependencyEvidence:
    dependency_task_id: str
    original_receipt_ref: str
    artifact_sha256: str

    def __post_init__(self) -> None:
        if not self.dependency_task_id or not self.original_receipt_ref:
            raise ValueError("DEPENDENCY_RECEIPT_REFERENCE_MISSING")
        if not _SHA.fullmatch(self.artifact_sha256):
            raise ValueError("DEPENDENCY_ARTIFACT_HASH_INVALID")

class DependencyReviewPort(Protocol):
    def verify_dependencies(
        self, project_id: str, plan_id: str, task_id: str,
        upstream_task_ids: tuple[str, ...],
    ) -> tuple[DependencyEvidence, ...]: ...
