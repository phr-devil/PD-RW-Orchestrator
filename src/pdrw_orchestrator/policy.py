"""Scoped operational guidance. Never a scientific authority or permit."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .models import TaskPacket

LEVELS = ("requirement", "must_consider", "recommendation", "experience")
RANK = {name: index for index, name in enumerate(LEVELS)}
_ALLOWED = {"id", "level", "source", "task_types", "text", "deny_effects",
            "evidence_refs", "conditions"}


@dataclass(frozen=True)
class Guidance:
    id: str
    level: str
    source: str
    task_types: tuple[str, ...]
    text: str
    deny_effects: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    conditions: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Guidance":
        if not isinstance(data, dict) or set(data) - _ALLOWED:
            raise ValueError("invalid guidance fields")
        for key in ("id", "level", "source", "text"):
            if not isinstance(data.get(key), str) or not data[key].strip():
                raise ValueError(f"guidance {key} missing")
        if data["level"] not in LEVELS:
            raise ValueError("unknown guidance level")
        if data["source"].lower().startswith(("experience", "distill")) and data["level"] != "experience":
            raise ValueError("experience source cannot claim a stronger level")
        names: dict[str, tuple[str, ...]] = {}
        for key in ("task_types", "deny_effects", "evidence_refs", "conditions"):
            values = data.get(key, [] if key != "task_types" else None)
            if not isinstance(values, list) or any(
                not isinstance(v, str) or not v.strip() for v in values
            ):
                raise ValueError(f"guidance {key} must be string list")
            names[key] = tuple(values)
        if not names["task_types"]:
            raise ValueError("task_types cannot be empty")
        if names["deny_effects"] and data["level"] != "requirement":
            raise ValueError("only user requirements can declare deny_effects")
        return cls(id=data["id"], level=data["level"], source=data["source"],
                   text=data["text"], **names)

    def applies(self, task: TaskPacket) -> bool:
        return "*" in self.task_types or task.task_type in self.task_types


@dataclass(frozen=True)
class GuidancePacket:
    rule_ids: tuple[str, ...]
    must_consider: tuple[str, ...]
    advisory: tuple[str, ...]
    denied_effects: tuple[str, ...]
    unresolved_conditions: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_ids": list(self.rule_ids),
            "must_consider": list(self.must_consider),
            "advisory": list(self.advisory),
            "denied_effects": list(self.denied_effects),
            "unresolved_conditions": list(self.unresolved_conditions),
            "permission_granted": False,
            "scientific_truth_verified": False,
        }


def load_policy(path: str | Path) -> tuple[Guidance, ...]:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("schema_version") != "1.0" or not isinstance(raw.get("rules"), list):
        raise ValueError("policy must have schema_version 1.0 and rules list")
    rules = tuple(Guidance.from_dict(item) for item in raw["rules"])
    ids = [rule.id for rule in rules]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate guidance ID")
    return rules


def experience_rules(raw: list[dict[str, Any]]) -> tuple[Guidance, ...]:
    """Untrusted provider entries cannot escalate to requirements."""
    prepared = []
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("experience lesson must be object")
        if item.get("level", "experience") != "experience":
            raise ValueError("experience cannot claim stronger authority")
        rule = Guidance.from_dict({**item, "level": "experience",
                                  "source": "experience:" + str(item.get("source", "unknown"))})
        prepared.append(rule)
    return tuple(prepared)


def compile_guidance(
    task: TaskPacket, rules: tuple[Guidance, ...], *,
    limit: int = 8,
) -> GuidancePacket:
    matching = sorted((r for r in rules if r.applies(task)),
                      key=lambda r: (RANK[r.level], r.id))
    ids = [r.id for r in matching]
    if len(set(ids)) != len(ids):
        raise ValueError("conflicting/duplicate rule IDs")
    mandatory = [r for r in matching if r.level in ("requirement", "must_consider")]
    if len(mandatory) > limit:
        raise ValueError("too many applicable mandatory rules; review configuration")
    chosen = mandatory + [r for r in matching if r not in mandatory][:limit-len(mandatory)]
    denied = sorted({effect for r in chosen for effect in r.deny_effects
                     if effect in task.required_effects})
    unknown = [r.id for r in chosen if r.conditions]
    return GuidancePacket(
        rule_ids=tuple(r.id for r in chosen),
        must_consider=tuple(r.id for r in chosen if r.level == "must_consider"),
        advisory=tuple(r.id for r in chosen if r.level in ("recommendation", "experience")),
        denied_effects=tuple(denied),
        unresolved_conditions=tuple(unknown),
    )
