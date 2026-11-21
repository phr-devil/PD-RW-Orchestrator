"""Portable, deliberately small task/result contracts."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

SCHEMA_VERSION = "1.0"
RESULT_STATUSES = frozenset({
    "DEMO_ONLY", "NOT_CONNECTED", "BLOCKED_AUTH", "BLOCKED_POLICY",
    "BLOCKED_DEPENDENCY", "FAILED", "NEEDS_REVIEW", "COMPLETED",
})


def _strings(items: Any, name: str) -> tuple[str, ...]:
    if not isinstance(items, (list, tuple)) or any(
        not isinstance(item, str) or not item.strip() for item in items
    ):
        raise ValueError(f"{name} must be a sequence of non-empty strings")
    return tuple(items)


@dataclass(frozen=True)
class TaskPacket:
    task_id: str
    project_id: str
    task_type: str
    objective: str
    capability: str = ""
    dependencies: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    protocol_refs: tuple[str, ...] = ()
    authorization_refs: tuple[str, ...] = ()
    required_effects: tuple[str, ...] = ()
    budget: dict[str, int] = field(default_factory=dict)
    idempotency_key: str = ""
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError("unsupported TaskPacket schema_version")
        for value in (self.task_id, self.project_id, self.task_type, self.objective):
            if not isinstance(value, str) or not value.strip():
                raise ValueError("task identity and objective must be nonempty")
        for name in ("dependencies", "evidence_refs", "protocol_refs",
                     "authorization_refs", "required_effects"):
            _strings(getattr(self, name), name)
        if len(set(self.dependencies)) != len(self.dependencies):
            raise ValueError("duplicate dependencies")
        if self.task_id in self.dependencies:
            raise ValueError("task cannot depend on itself")
        if not isinstance(self.capability, str) or not isinstance(self.idempotency_key, str):
            raise ValueError("capability/idempotency_key must be strings")
        if not isinstance(self.budget, dict) or set(self.budget) - {
            "max_attempts", "max_model_calls", "max_wall_seconds"
        }:
            raise ValueError("budget contains unsupported fields")
        for key, value in self.budget.items():
            if type(value) is not int or value < (0 if key == "max_model_calls" else 1):
                raise ValueError(f"invalid {key}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ResultPacket:
    task_id: str
    agent_id: str
    status: str
    details: str
    output_refs: tuple[str, ...] = ()
    scientific_verified: bool = False
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION or self.status not in RESULT_STATUSES:
            raise ValueError("invalid result schema or status")
        if not self.task_id or not self.agent_id:
            raise ValueError("missing result identity")
        _strings(self.output_refs, "output_refs")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
