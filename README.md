# PD-RW-Orchestrator

**Status: v0.1 / M1-B local intent store; mock execution only.** Evidence-aware, policy-guided coordination of specialist research agents. **Not an LLM; not yet connected to live ARC/AIDE/R&D-Agent.**

## Mission

Use external research agents to discover promising questions, design and implement algorithms, and review real evidence, while preserving one scientific workflow and the user's original decisions.

- **PD-RW** owns H1–H10 research policy, author decisions, and permitted actions.
- **Each research project** owns original protocols, STATE, RESEARCH_RECORD and immutable Runs.
- **PD-RW-Agent** provides research/Case Library context, read-only science checks and recovery through CLI/MCP.
- **This repository** owns only *operational* routing, task dependency management, policy-guidance selection, agent adapters and handoff transport.
- **PD-RW-Experience** will optionally supply sourced, conditional experience suggestions, never permissions or scientific conclusions.

### Getting started (Python 3.11+)

~~~bash
python -m pip install -e ".[dev]"
pdrw-orch doctor
pdrw-orch agents list
pdrw-orch policy check
pdrw-orch policy explain ALG-BASELINE --task-type experiment_design
pdrw-orch demo
python -m pytest -q
~~~

Mock execution never calls a model, downloads data, trains, edits scientific project files, reads SEALED or publishes. `DEMO_ONLY` is not a verified research Run.

### Local PD-RW-Agent read-only recovery

~~~powershell
# Only after the actual RC checkout and private project map are configured:
pdrw-orch pdrw inspect --project-id 19 --python "C:\\path\\to\\rc-venv\\Scripts\\python.exe"
~~~

See [bridge setup and limits](docs/PDRW_BRIDGE.md). Inspects one source-reported resume response using the RC CLI. It redacts source excerpts, never authenticates author permission, never restarts a process, and never changes a research project. GitHub CI uses simulated upstream responses only.

### New: restart-safe task intent storage (no execution)

~~~powershell
$env:PDRW_ORCH_RUNTIME_DIR = "D:\\private-orchestrator-runtime"
pdrw-orch schedule stage --file examples/operational-plan.example.json
pdrw-orch schedule inspect --project-id EXAMPLE --plan-id demo-research-001
~~~

See [local store and limits](docs/RUNTIME_STORE.md). The private DB contains operational task metadata only. Recording an intent never launches an agent and never permits an automatic retry.

### Core design

1. Task DAG and deterministic routing using declared capability plus confirmed adapter readiness.
2. Explicit task/result/handoff contracts; references rather than copied project evidence.
3. Fail-closed effects: no task with side effects can run until a trusted host implements authenticated approval and filesystem/network isolation.
4. Separate **P0 external authority**, **P1 user requirements**, **P2 must-consider**, **P3 recommendation**, **P4 experience advisory**.
5. Context-efficient guidance: only selected instructions with sources, conditions and evidence pointers; avoid reading irrelevant policies.
6. Real scientific review and external agent adapters remain later milestones.

### Repository navigation

- [Architecture](docs/ARCHITECTURE.md)
- [Policy system](docs/POLICY_SYSTEM.md)
- [Boundaries and readiness](docs/BOUNDARIES.md)
- [PD-RW-Agent bridge](docs/PDRW_BRIDGE.md)
- [Operational intent store](docs/RUNTIME_STORE.md)
- [User guide](docs/USER_GUIDE.md)
- [External adapter contract](docs/ADAPTERS.md)
- [Roadmap and acceptance](docs/ROADMAP.md)
- [External inspirations](docs/REFERENCES.md)

### Integrations

Existing PD-RW-Agent reference: [RC 1.0 architecture](https://github.com/phr-devil/PD-RW-Agent/blob/rc/v1.0-integration/docs/ARCHITECTURE.md). The RC head inspected for this integration was `9177b6eb822aaa0d1482ef40f54369a8612c42dd` (not proof of the version installed on your machine).

Agent backends are capability slots, not automatically installed or authorized. ARC/AIDE/R&D-Agent remain unavailable until real CLI/API handshake and bounded task acceptance pass. This repository does not vendor their implementations.

Never commit a private case library, manuscript, original Run, credentials or local machine data into this public repository.
