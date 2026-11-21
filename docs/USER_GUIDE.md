# User guide (M1-B local operational persistence)

~~~bash
python -m pip install -e ".[dev]"
pdrw-orch doctor
pdrw-orch agents list
pdrw-orch policy check
pdrw-orch policy explain ALG-BASELINE --task-type experiment_design
pdrw-orch demo
python -m pytest -q
~~~

The demo is mock-only: no actual research, GPU training or manuscript work.

## Read-only PD-RW-Agent source inspection

If the actual operator-machine RC package and private project map are available, see [PDRW_BRIDGE.md](PDRW_BRIDGE.md):

~~~powershell
pdrw-orch pdrw inspect --project-id 19 --python "C:\\path\\to\\python.exe"
~~~

This only reads source-reported compact context. It does not grant permission or certify a scientific claim.

## Private local scheduling intents

~~~powershell
$env:PDRW_ORCH_RUNTIME_DIR = "D:\\private-orchestrator-runtime"
pdrw-orch schedule stage --file examples/operational-plan.example.json
pdrw-orch schedule inspect --project-id EXAMPLE --plan-id demo-research-001
pdrw-orch schedule mark-uncertain --project-id EXAMPLE --plan-id demo-research-001 --task-id DISCOVERY-1 --attempt-id attempt-001
pdrw-orch schedule inspect --project-id EXAMPLE --plan-id demo-research-001
~~~

`mark-uncertain` only records a one-time intent for testing recovery semantics; it does not dispatch an Agent. It cannot be used to claim a test or real Run finished. See [RUNTIME_STORE.md](RUNTIME_STORE.md).

If the operator has a registered PD-RW project and the PD-RW-Agent CLI is installed, `schedule inspect --with-pdrw --project-id ID --plan-id PLAN --python PATH` combines both **read-only** reports. This cannot authenticate the user or grant execution.

Configuration files under `configs/*.example.yaml` and `policies/user/*.example.yaml` are examples. Local `*.local.yaml` copies are gitignored. Never put secrets or unpublished project state in the repository.

Production `start --project`, `resume`, `status`, `cancel` still require a verified trusted host, process supervision and actual agent integrations. They are not shipped in M1-B.
