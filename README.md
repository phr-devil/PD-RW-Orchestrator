# PD-RW-Orchestrator

## Specialist-project integration (development)

The primary purpose is to **reuse existing specialist research systems**, not
build a second PD-RW-Agent or recreate their search/experiment algorithms.
AIDE supports operator-staged DEV snapshots as well as the fixed pilot; AIDE and RD-Agent have bounded native task preparation/intake on a shared
public grouped synthetic pilot; ARC has limited discovery preview/intake.
The independent scorer runs without a model call. The shared `specialist-host` handoff supports all three native interfaces and unified `advise --intake-file` intake. No model-based specialist is launched automatically. An optional explicit public-network ToolUniverse Crossref lookup can reuse the native scientific tool without an LLM. See [specialist integration](docs/SPECIALIST_INTEGRATION.md)
for the pinned candidate catalog, current capability boundaries and commands.


**Status: v0.10.2 / pre-RC integration hardening. Actual upstream contract CI added; operator-host acceptance, original grants, real model runs and general research dispatch remain pending.** Evidence-aware, policy-guided coordination of specialist research agents. **Not an LLM; not yet connected to live ARC/AIDE/R&D-Agent.**

### M1-C host acceptance (no model calls)

~~~powershell
python -m pip install -e ".[host]"
pdrw-orch host audit --project-id 19 --python "D:\PD-RW-Agent\.venv\Scripts\python.exe"
# Only an operator-selected known PID:
pdrw-orch host process --pid 12345
~~~

See [M1-C host acceptance](docs/M1C_HOST_ACCEPTANCE.md). These checks are
read-only observations, not dispatch, original H6 permission, process
ownership, or restart authorization.

### M2-A: bounded two-provider synthetic relay

After a separately authorized successful `codex pilot` attempt in an isolated
environment, preview the second review (no model calls):

~~~powershell
pdrw-orch relay probe
pdrw-orch relay preview --plan-id pilot-001 --attempt-id attempt-001
~~~

Inspect the exact preview prompt, including selected Policy text, before
authorizing a second model. See [M2-A relay acceptance](docs/M2A_RELAY.md).
The general router is still non-dispatchable for real research; this is a
specialized fixed-scope pilot and not an authenticated H6 grant.

### M3-A: outcome-sensitive planning with Experience

`advise` now accepts an optional reported scientific outcome
(POSITIVE, NEGATIVE, MIXED, INCONCLUSIVE or INVALID) to focus independent
review without certifying science. For a locally installed, host-configured
PD-RW-Experience provider, add `--experience-config PATH`,
`--experience-query TERMS` and `--experience-as-of YYYY-MM-DD`.
Only a next research review/design task retrieves up to three advisory
lessons; original authority and current task guidance are unchanged.
See [Experience integration and decision semantics](docs/M3_EXPERIENCE.md).

### M4-A: compare research routes without spending model quota

After an advisory handoff, `pdrw-orch routes --handoff HANDOFF.json`
prints its decision-context fingerprint. Add `--options OPTIONS.json`
to compare bounded, evidence-linked operator-declared research options.
A Pareto frontier preserves tradeoffs rather than choosing a topic or
granting execution; matching Agent capability is a declared candidate,
not verified availability or performance. See [M4-A](docs/M4_ROUTE_COMPARISON.md).

### M4-B: offline historical and provider evaluation

`pdrw-orch benchmark replay --manifest CASES.json` runs the current
decision engine against explicitly time-bounded historical inputs.
`benchmark assess` compares a separate reference assessment;
`benchmark providers` compares two declared provider versions on a matched
cohort. No live project reads or model calls. See [M4-B](docs/M4_BENCHMARK.md).

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

### Original source cross-check (R2-B; read-only)

~~~powershell
# After configuring the actual PD-RW-Agent RC environment and private map:
pdrw-orch pdrw source-check --project-id 19 --operation-id OP-001 --run-id RUN-001
# Optional offline ChatGPT handoff, with exact original source refs:
pdrw-orch advise --task-file TASK.json --result-file RESULT.json --with-pdrw --source-operation-id OP-001 --source-run-id RUN-001
~~~

The original CLI checks only requested operation receipts and registered DEV/VAL
Run byte/structure evidence. It does **not** authenticate author H6 scope,
prove process liveness, permit retries, access SEALED or certify scientific
claims. Conflicting source/Task identities cause reconciliation. See
[original source check](docs/R2B_SOURCE_CHAIN.md) and
[requirements traceability](docs/REQUIREMENTS_TRACEABILITY.md).

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

### New: offline Agent-to-ChatGPT decision bridge (D1–D3)

~~~bash
pdrw-orch advise --task-file examples/decision-task.example.json --result-file examples/agent-result-v2.example.json
~~~

Returns a normalized untrusted result, conservative next-action recommendation, concise Agent task draft and six-section ChatGPT handoff report. Add `--save` only with a configured private `PDRW_ORCH_RUNTIME_DIR` to store `handoff.json` / `handoff.md` locally. **This does not run external Agents, verify science, or grant execution permission.** See [decision contract](docs/DECISION_AND_HANDOFF.md).

### R2-A: inspect the next Agent contract without running a model

~~~powershell
pdrw-orch codex contract
pdrw-orch codex probe
# Inspect a previously attempted private synthetic pilot:
$env:PDRW_ORCH_RUNTIME_DIR = "D:\\private-orchestrator-runtime"
pdrw-orch codex inspect --plan-id m2pilot-001 --attempt-id attempt-001
~~~

R2-A now compiles the scoped Pilot task and applicable policy into the actual
Codex stdin prompt, verifies only a **synthetic pilot** CLI capability, and
checks private host execution artifacts against recorded hashes. Neither
successful local hashes nor a CLI help probe proves science, host isolation,
paid usage, author grant, or general Agent readiness. See
[R2 contract and receipt specification](docs/R2_CONTRACT_EVIDENCE.md).

### Codex CLI synthetic read-only pilot (operator opt-in only)

~~~powershell
# First, no-cost capability check (no model call)
pdrw-orch codex probe --codex-bin "D:\\tools\\codex.exe"

# Only in an isolated environment and only after explicit external-model consent
$env:PDRW_ORCH_RUNTIME_DIR = "D:\\private-orchestrator-runtime"
pdrw-orch codex pilot --plan-id m2pilot-001 --attempt-id attempt-001 --codex-bin "D:\\tools\\codex.exe" --execute --ack-external-model
~~~

The pilot reads only the synthetic fixture in `examples/codex-pilot/`, records a
one-shot intent, and produces the existing untrusted-result → next-action →
ChatGPT handoff bundle. It never uses real research data or authorizations.
**The CLI read-only sandbox alone cannot guarantee strict file-visibility or
network isolation; use a disposable environment.** CI mocks the Codex executable;
a real Windows invocation is not yet verified.

See [Codex pilot and isolation limitations](docs/CODEX_PILOT.md).

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
- [Decision engine and ChatGPT handoff](docs/DECISION_AND_HANDOFF.md)
- [Codex CLI pilot (opt-in synthetic fixture)](docs/CODEX_PILOT.md)
- [Next-task transition and scope semantics](docs/TASK_TRANSITION.md)
- [User guide](docs/USER_GUIDE.md)
- [External adapter contract](docs/ADAPTERS.md)
- [Roadmap and acceptance](docs/ROADMAP.md)
- [External inspirations](docs/REFERENCES.md)

### Integrations

Existing PD-RW-Agent reference: [RC 1.0 architecture](https://github.com/phr-devil/PD-RW-Agent/blob/rc/v1.0-integration/docs/ARCHITECTURE.md). The RC head inspected for this integration was `9177b6eb822aaa0d1482ef40f54369a8612c42dd` (not proof of the version installed on your machine).

Agent backends are capability slots, not automatically installed or authorized. ARC/AIDE/R&D-Agent remain unavailable until real CLI/API handshake and bounded task acceptance pass. This repository does not vendor their implementations.

Never commit a private case library, manuscript, original Run, credentials or local machine data into this public repository.

The `specialists compile` command converts an explicit next TaskPacket and provider options into an existing native plan. It supports prior artifact byte comparison and a declared independent review reference without transferring grants. See [specialist integration](docs/SPECIALIST_INTEGRATION.md).

For real operator use, follow [concentrated specialist host acceptance](docs/SPECIALIST_HOST_ACCEPTANCE.md). AIDE and RD-Agent support staged custom DEV; public literature/dataset retrieval and explicit cross-provider task compilation are available. Live acceptance remains required.
