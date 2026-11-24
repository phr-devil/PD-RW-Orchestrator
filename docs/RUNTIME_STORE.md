# M1-B operational task intent storage (NOT a second research ledger)

The local private SQLite DB stores **immutable scheduling plans and task intent reservations only**. It does not store scientific metrics, raw evidence, original Run, authorization decisions, claim truth, or PD-RW-Agent's own operational receipts.

- Configure `PDRW_ORCH_RUNTIME_DIR` as a separate absolute private directory (not inside the Orchestrator repo, a PD-RW checkout, CASE_LIBRARY, original project root, or private project-map directory).
- `stage` writes an immutable task DAG and deterministic SHA-256 digest. Every task requires a unique, bounded idempotency key; re-staging the same `project_id + plan_id` with different content is a conflict.
- `inspect` opens SQLite read-only and does not create missing directories.
- `mark-uncertain` *only* reserves an operational dispatch intent; it does **not** start an Agent, grant access, or report successful execution. A missing response after any future dispatch is conservatively `RECONCILIATION_REQUIRED`.
- A dependent task cannot be reserved until independently validated upstream evidence and host reconciliation exist (not implemented). Intent IDs must be unique within a plan. The same intent ID cannot trigger a second dispatch; a different intent ID is rejected. A future trusted host must verify real process state, the original PD-RW-Agent operation receipt and source evidence **before** enabling an independent recovery operation.
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

## Host dependency-review port (v0.3, **not** real execution)

A downstream task with dependencies remains blocked unless an in-process
`DependencyReviewPort` is injected by a trusted host, returning source-linked
receipt references and artifact hashes for **every** upstream dependency.
The built-in CLI does not provide this port and cannot bypass the block.
The port's stub tests prove API/metadata behavior only; they do not prove a
real host or scientific evidence is trustworthy.

An accepted dependency review is stored as a pointer on the existing operational
`tasks` table, **not** a duplicate scientific Run ledger. Old SQLite databases
are migrated by adding one nullable column. Reserving a task still returns
`INTENT_UNCERTAIN_NO_DISPATCH`; it does not start an Agent, grant permission
or allow blind restart. A real host must verify actual process state and original
PD-RW operation receipts before authorizing any execution.

## Pre-RC integrity and cross-plan reconciliation

Each staged plan is revalidated against task hashes, the plan hash, DAG
and phase/intent consistency before reuse, inspection or reservation.
Hashes detect inconsistent local records, not a hostile rewrite of the
whole DB. A same-project non-PILOT reservation with the same task ID,
idempotency key or intent ID in another unresolved plan is rejected,
even when a new plan ID was chosen. Staging an alternative remains legal;
different projects and independent tasks are not globally blocked.
PILOT remains a fixed synthetic-only path with separate explicitly
opted-in plan sessions. This is not a cross-runtime or upstream global
exactly-once guarantee. Existing unresolved records are preserved; do
not delete them merely to get around the guard. No new scientific ledger.

The original PD-RW runtime directory is also protected from overlap.
Installed Wheels protect their own package directory rather than an
arbitrary parent of the interpreter's site-packages. DB leaf and SQLite
sidecars reject symlinks/reparse points/hard links; the private runtime
directory must still be operator-owned and is not an OS sandbox.
