# D1–D3: offline Agent result → next decision → ChatGPT handoff

**Status:** offline prototype. No live external Agent, trusted scientific reviewer, project authorization bridge or autonomous dispatch.

## Why these layers exist

A specialist Agent can finish an engineering step yet produce scientifically invalid or unproven claims. The planner should not blindly launch the next Agent on a self-reported result.

- **D1 / Result normalizer:** Accepts existing `ResultPacket v1` or agent-report v2 JSON. Exports **normalized result v2**, with separate reported execution, self-claimed scientific status, unverified artifact refs, limitations, and fixed `authorization_verified=false`, `effective_claim_status=NOT_ASSESSED`.
- **D3 / Next-action decision:** Deterministically chooses one *candidate* decision: RECONCILE, HOLD, REQUEST_AUTHOR_DECISION, REVISE_PLAN, SWITCH_AGENT or INDEPENDENT_REVIEW. Without host-verified science, READY_FOR_NEXT_STAGE is deliberately not reachable. Unconnected providers are NOT_CONNECTED and never selected as ready.
- **D2 / Instruction + ChatGPT handoff:** Emits a compact suggested Task Contract and a six-section ChatGPT-friendly summary. It quotes source-reported claims as untrusted data, includes only relevant Policy IDs/text and original source refs, and says it cannot dispatch.

`src/pdrw_orchestrator/models.py` `ResultPacket v1` and `schemas/result.schema.json` are intentionally unchanged. Any production v1→v2 conversion is one-way and does **not** upgrade science validity.

## Typical use

~~~powershell
pdrw-orch advise --task-file examples/decision-task.example.json --result-file examples/agent-result-v2.example.json
~~~

This prints a JSON bundle containing `result`, `decision`, `agent_instruction_draft`, and `chatgpt_handoff_md`. It never calls an LLM or another Agent.

To explicitly write the same machine/human reports into the private operational area (never a project root or Git checkout):

~~~powershell
$env:PDRW_ORCH_RUNTIME_DIR = "D:\\private-orchestrator-runtime"
pdrw-orch advise --task-file examples/decision-task.example.json --result-file examples/agent-result-v2.example.json --save
~~~

This creates `handoff.json`, `handoff.md` and `COMPLETE.json` in a content-addressed directory. The original project/Run and PD-RW-Agent receipt databases are not modified. The saved report is not a scientific record and does not authenticate any authorization.

## Routing principles

1. Determine whether original source/context needs reconciliation before proposing new operations.
2. Apply applicable P1 effect denials; a P1 YAML setting is not an authorization grant.
3. A missing host effect authorization cannot be fixed by switching Agents.
4. A successful execution report with referenced artifacts asks for independent science review, **not** readiness for publication.
5. With current registry all real providers are unconnected. Output an intended *capability*, declared-but-unavailable candidates and a null verified agent. Mock providers are never mistaken for actual research experts.
6. Minimize tokens: do not duplicate all upstream case records. Limit reported findings to 16, lesson guidance to the small selected set, and return refs not document bodies.
7. On critical uncertainty, propose review/reconciliation. Future trusted host bridges may provide attested evidence, but no free-form JSON field named VERIFIED can grant this.

## Remaining work

- M1-C real workbench recovery smoke test (original identity/receipt/process reconciliation).
- First real **read-only** Agent Adapter health and bounded handoff. Until real execution control is developed, output remains DRAFT_ONLY.
- Trusted independent science review and deterministic agent-choice acceptance against real capability measurements.
- PD-RW-Experience source/temporal validation as an advisory input only.

## R1 decision safeguards

- An execution failure is classified as an *engineering/task failure* before
  attempting to recheck author grant references. Existing source-scope status
  remains visible and never becomes a permission.
- A completed review does not automatically create another independent review.
  Instead `REVIEW_OUTCOME_PENDING` targets a `human_assessment` proposal,
  with no verified Agent, no automatic dispatch and no claim of scientific truth.
- `SWITCH_AGENT` preserves the original task capability when searching for
  a replacement specialist. Its proposal remains a non-dispatchable candidate.
- Branch/attempt-specific next-task IDs prevent collisions across distinct
  result attempts while retaining original evidence references.
