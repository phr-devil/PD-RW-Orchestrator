# User guide — v0.6.1 (R2-B read-only source checks; execution pilot separate)

~~~bash
python -m pip install -e ".[dev]"
pdrw-orch doctor
pdrw-orch agents list
pdrw-orch policy check
pdrw-orch demo
pdrw-orch advise --task-file examples/decision-task.example.json --result-file examples/agent-result-v2.example.json
python -m pytest -q
~~~

The `advise` command generates a machine-readable normalized Agent report, proposed next-action decision, concise draft instruction and ChatGPT-oriented six-section report. It does not call any external Agent, cannot authorize execution, and cannot verify scientific results.

To explicitly save `handoff.json` and `handoff.md`, configure a private absolute `PDRW_ORCH_RUNTIME_DIR` outside source repositories and original science projects, then add `--save`. See [decision/handoff docs](DECISION_AND_HANDOFF.md).

Other existing commands remain available:

- `pdrw-orch pdrw inspect --project-id ID` (requires actual operator-machine PD-RW-Agent RC and private project map; read-only, not yet machine-validated).
- `pdrw-orch schedule stage --file examples/operational-plan.example.json` (local intent, no dispatch).
- `pdrw-orch schedule inspect --project-id EXAMPLE --plan-id demo-research-001` (read-only status).
- `pdrw-orch schedule mark-uncertain ...` (test one-time intent, does not execute).

No live ARC/AIDE/R&D-Agent is connected; real WorkBuddy integration requires M1-C/M2 host controls.

## Codex pilot (opt-in real subprocess, synthetic only)

~~~powershell
pdrw-orch codex probe --codex-bin "D:\\tools\\codex.exe"
$env:PDRW_ORCH_RUNTIME_DIR = "D:\\private-orchestrator-runtime"
pdrw-orch codex pilot --plan-id m2pilot-001 --attempt-id attempt-001 --codex-bin "D:\\tools\\codex.exe" --execute --ack-external-model
~~~

Only run this with a locally installed, authenticated native CLI and in an
isolated environment. The external model may incur usage charges. No real
scientific data, live agent chaining or write-enabled task is supported.
See [CODEX_PILOT.md](CODEX_PILOT.md).

## Original source check (requires trusted local PD-RW-Agent RC)

~~~powershell
$env:PDRW_AGENT_CONFIG = "D:\private\project-map.json"
$env:PDRW_WORKFLOW_ROOT = "D:\local\Problem-Data-Research-Workflow"
pdrw-orch pdrw source-check --project-id 19 --operation-id OP-001 --run-id RUN-001
~~~

Paths and IDs are placeholders. Only the supplied original operation and
DEV/VAL Run metadata are checked. No author permission, scientific verdict
or process restart can result. For task-specific advice, add
`--with-pdrw --source-operation-id OP-001 --source-run-id RUN-001` to
`advise`. The original task ID must match the source declaration.
See [R2-B source checks](R2B_SOURCE_CHAIN.md).

## Ordinary Wheel install (v0.6.2)

The package now includes the non-sensitive default Agent Registry, Policy,
Codex synthetic fixture and output Schema, so `doctor`, `codex contract`,
and the fixed synthetic pilot file checks can run from a regular Wheel install
without a source checkout. The bundled assets are **examples only**, never
original H6 author grants or scientific source files. For editable installs,
repo assets remain authoritative and are hash checked; missing/changed source
fixtures are not replaced silently.

For a production original project, supply actual private project mapping
via `PDRW_AGENT_CONFIG` and PD-RW rule checkout via
`PDRW_WORKFLOW_ROOT`. The Wheel does not include private project data,
PD-RW-Agent or any real execution permission.

## M1-C operator host audit (v0.7.0)

Install with `python -m pip install -e ".[host]"` for optional psutil
process observations. Run `pdrw-orch host audit --project-id ID --python PATH`
with original private map and rules configured; specify actual operation/Run
IDs and an optional expected task ID only when applicable. Observe an
operator-selected PID with `pdrw-orch host process --pid PID`.
See [M1-C host acceptance](M1C_HOST_ACCEPTANCE.md) for exact semantics.
