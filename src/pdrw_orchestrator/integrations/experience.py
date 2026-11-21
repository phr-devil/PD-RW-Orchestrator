"""Provider contract boundary. Only advisory lessons may cross it."""
from pdrw_orchestrator.policy import Guidance, experience_rules


def accept_advisories(items: list[dict]) -> tuple[Guidance, ...]:
    return experience_rules(items)
