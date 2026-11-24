# R2-B / M1-C — original PD-RW source cross-check (read-only subset)

**Status:** R2-B source-validation interfaces implemented with simulated upstream
CI. Actual operator-machine M1-C acceptance, author-grant verification and
true Agent dispatch **remain pending**.

## Source authority (do not create parallel scientific ledgers)

- The original project/PD-RW owns H3/H4/H6/H8 author choices, protocol,
  RESEARCH_RECORD, STATE, immutable scientific Runs, and source permissions.
- PD-RW-Agent RC owns read-only original source checks and existing operational
  receipts. The current adapter targets the RC CLI:
  \`resume --project-id ID\`, \`operations --project-id ID --operation-id OP\`,
  and \`verify-run --project-id ID --run-id RUN\`.
- This repo is strictly an **operational** orchestrator. It stores no replica
  of Run contents or scientific ledger, never edits upstream records, and never
  interprets an Agent's claim as author permission.

## Validation sequence

1. Verify exact local project registration in \`PDRW_AGENT_CONFIG\` (schema 1),
   relevant PD-RW rule checkout, and trusted operator-selected Python.
2. Read one \`resume\` response for identity and recovery blockers.
   A blocked original project stops subsequent checks.
3. Optionally fetch one original operation receipt with \`operations\`,
   preserve \`recovery_class\`, phase and artifact-integrity indicator,
   **not** raw paths, logs or scientific documents.
4. Optionally check one DEV/VAL Run using original \`verify-run\`. A status
   \`RUN_BYTES_MATCHED_ONLY\` means registered files and declared links match,
   **not** scientific validity, independent sampling, or experiment legality.
   \`RUN_SOURCE_MATCHED_ONLY\` represents matching source metadata but a
   non-VALID declared Run, **not** a scientific negative.
5. If both operation and Run were requested, compare original task-ID
   declarations. Mismatch, missing receipt, protected data or uncertain
   process state causes reconciliation, not blind retry or project pivot.

No private research file is opened *by Orchestrator* and no raw upstream body
is included in the response. Only bounded allowlisted original statuses and
hashes are emitted. The source Python CLI does access registered original
project files in accordance with its upstream read-only contract. Use only
the correctly installed trusted RC and your original project map.

### Example (Windows PowerShell)

~~~powershell
$env:PDRW_AGENT_CONFIG = "D:\\private\\project-map.json"
$env:PDRW_WORKFLOW_ROOT = "D:\\PD-RW"
pdrw-orch pdrw source-check --project-id 19 --operation-id OP-001 --run-id RUN-001 --python "D:\\PD-RW-Agent\\.venv\\Scripts\\python.exe"
~~~

IDs and paths are **illustrative placeholders**. Never supply SEALED,
holdout or confirmation artifacts. You may omit \`--operation-id\` or
\`--run-id\` to perform only the applicable read-only checks.

To include a specific source cross-check in an offline ChatGPT handoff:

~~~powershell
pdrw-orch advise --task-file TASK.json --result-file RESULT.json --with-pdrw --source-operation-id OP-001 --source-run-id RUN-001
~~~

A mismatched original task ID, unknown old process, incomplete original
receipt or Run problem produces a \`RECONCILE\` decision. The source check
never upgrades \`effective_claim_status\` to VALID and never authorizes
\`local_dev_execution\`, model calls, SEALED, manuscript writing or submission.

## Explicit pending boundaries

- Real Windows operator-machine project identity and original receipts must
  be checked, including whether RC source, Skill and CLI are the **same
  installed revision**. Do not assume a pip metadata version is current.
- \`process_liveness_verified\`, \`author_scope_verified\`,
  \`project_identity_authenticated\` and \`scientific_validity_verified\`
  remain **false**. File-hash consistency is not original H6 permission and
  cannot verify scientific claims.
- Operational receipt state \`RUNNING_DECLARED\` is **not** proof an OS
  process is alive; no automatic restart is permitted.
- Previous valid DEV work can continue *under independently verified original
  scope*, but this read-only bridge cannot itself issue that verification.
  No repeated author approval should be requested merely because scope
  verification is pending.
- Research decisions must distinguish TRUE NEGATIVE, INVALID, UNKNOWN and
  ENGINEERING_FAILURE; all source checks are evidence prerequisites, not
  scientific classifications.
- Next: real operator-host process/permissions adapter with explicit original
  scope authorizer; then bounded real-Agent handoff and independent review.
