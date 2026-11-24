# R2-A — Task contract, scoped capability, and local host evidence

Status: **v0.5.0, code and synthetic cross-platform CI only**.

The scoped Codex pilot now connects three interfaces.

## 1. Task Contract Compiler

`contracts.compile_pilot_contract(task,guidance)` emits a bounded, stable,
SHA-256-identifiable **synthetic-only** task contract. This includes:
- exact project/task identity and review objective;
- only applicable, bounded guidance and its provenance/advisory status;
- planned wall/attempt/model-call *targets* (not measured spend);
- no effects, inherited original authorization or real dataset references;
- acceptance criteria, stop conditions and disclaimer.

The compiled JSON is rendered as **data inside the actual Codex stdin prompt**
(in place of a fixed prompt that previously omitted the Policy Engine).
Only the fixed public fixture may be supplied; a contract specifying a real
research project, protected effect, private evidence or different task is
rejected before reservation.

The prompt is NOT a security enforcement mechanism. Existing prompt injection
or host permissions are not proven secure by unit tests; use OS isolation.

## 2. Agent capability: handshake is not general readiness

`capabilities.accept_codex_pilot_probe` combines a real CLI help/version
probe, the registered adapter/capability, and **exact PILOT task identity**.
It can mark `PILOT_SYNTHETIC_READONLY_ONLY` supported, but the snapshot always
keeps `general_research_ready=false`,
`credentials_verified=false`, `host_isolation_verified=false`, and
`execution_authorized=false`.

The production/general Router remains fail-closed for non-Mock adapters.
This initial capability proof may only select the fixed Pilot, not original
research, write-enabled DEV or arbitrary generated next tasks.

## 3. Local execution evidence

Before a model launch, a private copy of the exact `task-contract.json`
is stored alongside the operational attempt. Following the *attempted*
subprocess, `host-execution.json` records local observed return code and
bounded artifact hashes, including the compiled task contract SHA-256.
`host_evidence.inspect_pilot_receipt` checks local bytes, attempt identity,
receipt/contract linkage and output hash.

**LOCAL_BYTES_MATCH_NOT_SCIENCE** means only these local files match; the
records are not signed, not independent scientific evidence, not an actual
model usage or payment receipt, and never a grant from PD-RW or the author.
Any inconsistent file returns `HOST_RECEIPT_RECONCILIATION_REQUIRED`,
and restarting remains blocked.

## CLI — safe, no model calls

~~~powershell
# Preview exactly which policy-derived contract would be sent
pdrw-orch codex contract

# CLI version/flags plus scope-limited pilot capability inspection
pdrw-orch codex probe --codex-bin "D:\\tools\\codex.exe"

# After a separately opted-in pilot, inspect stored local attempt integrity
$env:PDRW_ORCH_RUNTIME_DIR = "D:\\private-orchestrator-runtime"
pdrw-orch codex inspect --plan-id m2pilot-001 --attempt-id attempt-001
~~~

No real Codex call was made by GitHub CI. The `pilot` subcommand still
requires `--execute --ack-external-model` in an isolated operator environment.

## Future R2-B / M1-C

Still NOT implemented: a trusted host grant verifier, real PD-RW receipt and
original artifact authentication, actual subprocess credentials/usage proof,
general Agent routing, second Agent handoff, process-liveness/cancellation,
and authorization to use private project files.

Implement those against the operator's controlled machine and verify actual
PD-RW scientific source first. Do not widen scope based solely on JSON claims
or a valid SHA string.
