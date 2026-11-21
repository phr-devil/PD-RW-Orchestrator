"""Capability registry; config readiness is not host readiness."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class AgentSpec:
    id: str
    adapter: str
    capabilities: tuple[str, ...]
    ready: bool
    priority: int

    @property
    def verified_ready(self) -> bool:
        # Only an in-process deterministic mock adapter ships today.
        return self.adapter == "mock" and self.ready


def load_agents(path: str | Path) -> tuple[AgentSpec, ...]:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("schema_version") != "1.0" or not isinstance(raw.get("agents"), list):
        raise ValueError("registry schema_version or agents invalid")
    specs = []
    for data in raw["agents"]:
        if not isinstance(data, dict) or set(data) - {"id", "adapter", "capabilities", "ready", "priority"}:
            raise ValueError("agent fields invalid")
        if not isinstance(data.get("id"), str) or not data["id"].strip():
            raise ValueError("agent id invalid")
        if not isinstance(data.get("adapter"), str) or not data["adapter"].strip():
            raise ValueError("agent adapter invalid")
        caps = data.get("capabilities")
        if not isinstance(caps, list) or not caps or any(not isinstance(c, str) or not c for c in caps):
            raise ValueError("agent capabilities invalid")
        if type(data.get("ready")) is not bool:
            raise ValueError("ready must be boolean")
        priority = data.get("priority", 100)
        if type(priority) is not int:
            raise ValueError("priority must be integer")
        specs.append(AgentSpec(id=data["id"], adapter=data["adapter"],
                               capabilities=tuple(caps), ready=data["ready"], priority=priority))
    if len({a.id for a in specs}) != len(specs):
        raise ValueError("duplicate agent ID")
    return tuple(specs)
