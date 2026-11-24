"""Live CLI capability snapshot limited to this public synthetic Pilot.

No untrusted disk JSON or Agent claim can set general agent readiness.
Handshake != authentication, read isolation, cost control or science success.
"""
from __future__ import annotations

from dataclasses import dataclass
from .models import TaskPacket
from .registry import AgentSpec


@dataclass(frozen=True)
class PilotCapability:
    agent_id: str
    adapter: str
    scope: str
    supported: bool
    cli_version: str | None
    credentials_verified: bool = False
    host_isolation_verified: bool = False
    general_research_ready: bool = False

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "adapter": self.adapter,
            "scope": self.scope,
            "supported": self.supported,
            "cli_version": self.cli_version,
            "credentials_verified": False,
            "host_isolation_verified": False,
            "general_research_ready": False,
            "execution_authorized": False,
        }


def accept_codex_pilot_probe(probe, agents: tuple[AgentSpec, ...],
                             task: TaskPacket) -> PilotCapability:
    matched = [a for a in agents if a.id == "codex-local" and a.adapter == "codex"]
    accepted = bool(
        len(matched) == 1
        and "review" in matched[0].capabilities
        and getattr(probe, "supported", False) is True
        and getattr(probe, "status", None) == "CLI_CAPABILITY_PROBE_OK"
        and getattr(probe, "executable", None)
        and task.project_id == "PILOT"
        and task.task_id == "CODEX-READ-001"
        and task.capability == "review"
        and task.task_type == "review"
        and not task.required_effects
    )
    return PilotCapability(
        agent_id="codex-local", adapter="codex",
        scope="PILOT_SYNTHETIC_READONLY_ONLY",
        supported=accepted,
        cli_version=getattr(probe, "version", None),
    )
