# User guide — offline v0.2 decision and handoff prototype

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
