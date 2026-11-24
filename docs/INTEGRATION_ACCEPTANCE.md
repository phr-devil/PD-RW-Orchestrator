# Pre-RC integration acceptance (v0.10.2)

Scope: Orchestrator only. Original rules, project data and authorization
remain owned by their original sources.

| Component | CI reference |
|---|---|
| PD-RW-Agent | 9177b6eb822aaa0d1482ef40f54369a8612c42dd (RC 1.0.0rc1) |
| PD-RW | d4056fc10af89c3ecfd41ece15c55440d21c33e1 |
| Experience | 6f22e958233e1313171f4a6317642e0390445d10 (0.2.0a1) |

These are CI reference commits, not automatic upgrades or proof of the
operator's installation. The main branch of PD-RW-Agent is not substituted
for the RC. CI creates only public synthetic fixtures, records a Run using
the actual PD-RW core writer, seeds an operational receipt via the actual
upstream service, then uses Orchestrator's read-only subprocess bridge.
The test compares original project bytes before/after and tampers with
a synthetic linked artifact to check rejection. Experience retains its
separate signed synthetic contract test.

## Source audit corrections

Retain original protocol identity, declared latest valid Run ID, host
reconciliation hint and independent permitted read-only review hint.
Reject contradictory receipt statuses/rows and recovery classes; bound
actual file reads rather than only pre-read stat size. JSON input accepts
a UTF-8 BOM for Windows portability. Handoff Markdown carries the same
bounded source status already present in JSON. A source-reported independent
read-only hint is not a grant, proof of task independence, or permission to
restart an unresolved job. Affected task reconciliation still takes
precedence. Do not globally prohibit separately established lawful work.

## One operator pass

1. Update Orchestrator in its own checkout, then install with
   python -m pip install -e ".[host]". Do not overwrite an existing
   PD-RW-Agent checkout with a different version.
2. Configure the original private project map, original workflow root
   and disjoint private Orchestrator runtime directory. The upstream
   PDRW_RUNTIME_DIR must also be independent of the project, rules checkout
   and the project map's parent directory (including ancestors/descendants).
3. Run host audit with the actual project ID and selected PD-RW-Agent
   Python interpreter; use original operation/Run IDs when available.
4. Run advise with the actual task/result files and --with-pdrw.
   Review the original source status and proposed next task; no model
   dispatch is performed. Optional Experience retrieval uses its own
   trusted operator config and original visibility cutoff.

See M1C_HOST_ACCEPTANCE.md and M3_EXPERIENCE.md for commands.
A source byte match is not science or a grant. Still missing: authenticated
original H6 scope, trusted real-project operation/process binding,
actual provider isolation and measured real Agent handoff. These are
release blockers for a real-execution v1.0, not synthetic test failures.

## Lifecycle audit follow-up

The pinned Agent RC host/authorization.py validates DEV declarations via
host/contracts.py; preview_dev_admission returns TRUSTED_HOST_NOT_CONNECTED
or PROJECT_MACHINE_STATE_BLOCKED, never execution_authorized. The
submit_dev_in_trusted_host and register_run_in_trusted_host interfaces
are deliberately disabled. Do not connect a caller-provided callback or
a grant JSON as a substitute. A separate trusted OS/tool host must enforce
original authority, frozen task/code/dataset bindings, filesystem scope,
process isolation and resource limits. Orchestrator can reuse the existing
DEV proposal shape and preview, but cannot implement a real grant by
itself. Ordinary existing-scope DEV should not require fresh author
approval when that original grant is verifiable.

Local plan integrity and cross-plan unresolved-intent protection now
prevent accidental re-reservation. This does not authenticate the DB,
establish dependency evidence validity or replace the upstream receipts.

## Pre-RC operator entry points

Use one read-only configuration pass:
~~~powershell
pdrw-orch doctor --project-id PROJECT --python PATH_TO_AGENT_PYTHON
~~~
The optional project form checks local policy/registry shape, runtime directory
separation (no creation), and installed RC/source observation. Exit 0 means
these diagnostic checks completed, not readiness to execute. Exit 3 means
reconciliation required; the original no-argument doctor remains compatible.

For an actual frozen DEV declaration:
~~~powershell
pdrw-orch host admission --plan-file DEV_PROPOSAL.json --python PATH_TO_AGENT_PYTHON
~~~
Use the upstream host/contracts.py pdrw-dev-plan-v1 schema, not the unrelated
CPU_SELFTEST_V1 execution-preflight CLI schema. The adapter calls the installed
RC host.authorization.preview_dev_admission in an isolated interpreter,
checks the returned identity/digest and all false authorization/runtime flags,
and rejects config/rule sample drift. No submit, Run registration, receipt
write, execution or grant is performed. The selected interpreter/package is
operator-trusted; version agreement and sampled fingerprints are not a
full revision or OS identity authentication. A successful preview means the
upstream accepted the declaration, not that its referenced hashes were
verified or a task is executable.

Release gate: a separate authenticated OS/tool host must validate original
H6 scope against frozen task/code/dataset, enforce filesystem/network and
resource constraints, bind operation to actual process, and register evidence
through the original workflow. Missing verifier does not mean fresh H6 is
required. This gate remains upstream work; no synthetic test can close it.
