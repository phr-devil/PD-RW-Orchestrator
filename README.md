# PD-RW-Orchestrator

**Status: v0.1 foundation / dry-run only.** Evidence-aware, policy-guided coordination of specialist research agents. **Not an LLM, not a scientific authority, not yet connected to ARC/AIDE/R&D-Agent.**

## Mission

Use external research agents to discover promising questions, design and implement algorithms, and review real evidence, while preserving one scientific workflow and the user's original decisions.

- **PD-RW** owns H1–H10 research policy, author decisions, and permitted actions.
- **Each research project** owns original protocols, STATE, RESEARCH_RECORD and immutable Runs.
- **PD-RW-Agent** provides research/Case Library context, read-only science checks and recovery through CLI/MCP.
- **This repository** owns only *operational* routing, task dependency management, policy-guidance selection, agent adapters and handoff transport.
- **PD-RW-Experience** will optionally supply sourced, conditional experience suggestions, never permissions or scientific conclusions.

### First-use commands (Python 3.11+)

~~~bash
python -m pip install -e ".[dev]"
pdrw-orch doctor
pdrw-orch agents list
pdrw-orch policy check
pdrw-orch policy explain ALG-BASELINE --task-type experiment_design
pdrw-orch demo
python -m pytest -q
~~~

These commands run with **mock adapters only**. No external model call, download, training, scientific project edit, SEALED read or publication occurs. Do not interpret mock results as a verified research Run.

### Core design

1. Task DAG and deterministic routing using **declared capability plus confirmed adapter readiness**.
2. Explicit task/result/handoff contracts; references rather than copied project evidence.
3. Fail-closed effects: no task with real side effects can run until a *trusted host* has implemented authenticated authorization and filesystem/network isolation.
4. Separate **P0 external authority**, **P1 user requirements**, **P2 must-consider**, **P3 recommendation**, **P4 experience advisory**. A YAML file is not an authorization grant.
5. Context-efficient guidance: select applicable rules only; no full-context reload or mandatory audits per routine DEV.
6. Durable execution, real scientific review, and external adapters are later milestones, not advertised as complete.

### Repository navigation

- [Architecture](docs/ARCHITECTURE.md)
- [Policy system](docs/POLICY_SYSTEM.md)
- [Boundaries and readiness](docs/BOUNDARIES.md)
- [User guide](docs/USER_GUIDE.md)
- [External adapter contract](docs/ADAPTERS.md)
- [Roadmap and acceptance](docs/ROADMAP.md)
- [External inspirations](docs/REFERENCES.md)

### Integrations

Existing PD-RW-Agent reference: [RC 1.0 architecture](https://github.com/phr-devil/PD-RW-Agent/blob/rc/v1.0-integration/docs/ARCHITECTURE.md). Pin the actual checked-out commit; its default main branch may differ from RC. Never migrate its science records or reproduce its rules here.

Agent backends are *capability slots*, not automatically installed or authorized. An agent labelled ARC, AIDE or R&D-Agent is unavailable until its actual CLI/API handshake and bounded task acceptance pass. For now the registry intentionally enables only mock adapters.

No credential, private paper, internal Run, or CASE_LIBRARY bytes belong in this public repository.
