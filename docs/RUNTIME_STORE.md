# M1-B operational task intent storage (NOT a second research ledger)

The local private SQLite DB stores **immutable scheduling plans and task intent reservations only**. It does not store scientific metrics, raw evidence, original Run, authorization decisions, claim truth, or PD-RW-Agent's own operational receipts.

- Configure `PDRW_ORCH_RUNTIME_DIR` as a separate absolute private directory (not inside the Orchestrator repo, a PD-RW checkout, CASE_LIBRARY, original project root, or private project-map directory).
- `stage` writes an immutable task DAG and deterministic SHA-256 digest. Re-staging the same `project_id + plan_id` with different content is a conflict.
- `inspect` opens SQLite read-only and does not create missing directories.
- `mark-uncertain` *only* reserves an operational dispatch intent; it does **not** start an Agent, grant access, or report successful execution. A missing response after any future dispatch is conservatively `RECONCILIATION_REQUIRED`.
- The same intent ID cannot trigger a second dispatch; a different intent ID is rejected. A future trusted host must verify real process state, the original PD-RW-Agent operation receipt and source evidence **before** enabling an independent recovery operation.
- `assess_recovery(local, upstream)` combines read-only statuses but never authenticates identity, user decisions, original Run or execution permission.

## Usage on Windows PowerShell

~~~powershell
$env:PDRW_ORCH_RUNTIME_DIR = "D:\\private-orchestrator-runtime"
pdrw-orch schedule stage --file examples/operational-plan.example.json
pdrw-orch schedule inspect --project-id EXAMPLE --plan-id demo-research-001
pdrw-orch schedule mark-uncertain --project-id EXAMPLE --plan-id demo-research-001 --task-id DISCOVERY-1 --attempt-id attempt-001
pdrw-orch schedule inspect --project-id EXAMPLE --plan-id demo-research-001
~~~

**The example plan is synthetic.** Status after `mark-uncertain` is intentionally unresolved and non-runnable. Nothing actually executes and no PID is invented. For `pdrw-orch pdrw inspect`, see [PDRW_BRIDGE.md](PDRW_BRIDGE.md).

### M1-B acceptance boundary

Schema, persistence, idempotency and restart-fail-closed behavior can be tested in GitHub CI. **Real operator-machine acceptance remains pending**: PD-RW-Agent RC must be installed and its private project map must contain an authorized project. That test requires the user's machine; GitHub runners cannot inspect it.

This private runtime DB is an *operational queue*, not a second source of scientific truth. If a future engine needs more complex durable execution, compare adopting LangGraph's persistence or another maintained runner instead of expanding a duplicate job supervisor here.
