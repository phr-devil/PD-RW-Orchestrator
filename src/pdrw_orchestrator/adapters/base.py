"""All adapters must return an explicit structured result."""
from typing import Protocol

from pdrw_orchestrator.models import ResultPacket, TaskPacket
from pdrw_orchestrator.policy import GuidancePacket
from pdrw_orchestrator.registry import AgentSpec


class AgentAdapter(Protocol):
    def run(self, task: TaskPacket, guidance: GuidancePacket, agent: AgentSpec) -> ResultPacket: ...
