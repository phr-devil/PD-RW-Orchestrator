# M4-B — offline historical replay and provider assessment (v0.10.1)

The current engine can be tested on an operator-owned frozen historical
cohort. This is not historical reconstruction of past software versions.
Do not publish private project records or feed post-decision summaries to
the replay. Use original frozen inputs and original evidence of availability.
No live PD-RW/Experience retrieval, paid model call or experiment execution.

## Historical replay

The input is deliberately separate from the later reference assessment.
Freeze every eligible case before evaluating outcomes, including failures
and cases whose original inputs cannot be recovered.

~~~json
{"schema_version":"1.0","reference_commitment_sha256":null,
 "cases":[{"case_id":"C1","cutoff":"2026-11-15T12:00:00+09:00",
 "input_status":"AVAILABLE","availability_refs":["original-freeze-ref"],
 "inputs":{
 "task":{"project_id":"P","task_id":"T","task_type":"code_experiment","objective":"Evaluate"},
 "result":{"schema_version":"2.0","project_id":"P","task_id":"T","agent_id":"aide","attempt_id":"A","execution":{"status":"FAILED"}},
 "source_context":null,
 "available_at":{"task":"2026-11-15T10:00:00+09:00","result":"2026-11-15T11:00:00+09:00","source_context":null}
 }}]}
~~~

The example is synthetic. For missing originals set input_status UNAVAILABLE
and inputs null; preserve the case in the cohort. Every timestamp needs a
timezone. A declared future input rejects the manifest. Availability refs
must cite original frozen events or reliable version history; timestamps
and refs supplied to this command are not independently authenticated.
A null source_context means no historical source snapshot was provided,
not that the source was valid. Current policy/registry and engine version
are recorded with digests. The actual normalize_result/decide_next path
is exercised, not a parallel decision simulator.

~~~powershell
pdrw-orch benchmark replay --manifest CASES.json
~~~

Save stdout as a UTF-8 JSON file locally (PowerShell 7 or use an explicit
UTF-8 writer). Use the original case hashes from the replay and canonical
digest function pdrw_orchestrator.experience_evaluation.digest.

The independent reference is a separate file:

~~~json
{"schema_version":"1.0","replay_sha256":"COPY_CANONICAL_REPLAY_DIGEST",
 "cases":[{"case_id":"C1","case_sha256":"COPY_CASE_DIGEST",
 "reference_status":"REVIEWED_DECLARED","acceptable_decisions":["REVISE_PLAN"],
 "evidence_refs":["independent-reference-assessment"]}]}
~~~

Reference statuses are REVIEWED_DECLARED and UNKNOWN (empty acceptable
decisions). Multiple reasonable actions can be accepted. Pre-register
the reference cases array and put its canonical digest in
reference_commitment_sha256 before replay; case hashes are digest(case)
and can be computed before replay. The commitment matches the exact array
but does not authenticate when it was made. Null allows exploratory
evaluation without a commitment. Independently preserve the commitment in
a timestamped trusted source before inspecting the replay.

~~~powershell
pdrw-orch benchmark assess --manifest REFERENCE.json --replay REPLAY.json
~~~

Every original case must be retained, with an exact case hash.
Report match rate among assessed cases and match fraction of the full
cohort separately, with unknown and missing inputs visible. These are
descriptive decision-category metrics, not scientific validity or
publication outcomes. Review reference choices blindly where possible.
Never use later H8 choices as the only acceptable label when several
actions were reasonable at the original time.

## Matched provider assessment

~~~powershell
pdrw-orch benchmark providers --manifest PROVIDERS.json
~~~

Format: schema_version 1.0, capability, providers (exactly two objects
with agent_id, version, config_sha256), cases (1–100 unique case IDs).
Each case contains case_id, protocol_sha256, budget (tokens and
wall_seconds positive integers), arms (two objects in provider order).
Each arm contains agent_id, provider_sha256 (canonical digest of the
provider object), protocol_sha256, status (COMPLETED/FAILED/UNKNOWN/
NOT_RUN), result_ref, reviewer_ref, rubric, tokens, wall_seconds.
Use null for unavailable fields; completed or failed arms require
distinct result references. Noncompleted arms cannot claim rubric scores.
Rubric is null if not assessed, otherwise the existing four binary
dimensions source_legality, scientific_validity, decision_relevance,
avoids_redundant_work.

Freeze common original evidence, task, allowed tools, budget, scoring
rubric, and review process in the actual protocol document before both
runs. Bind exact provider version/config. These hashes are declared
bindings, not proof the provider actually respected the protocol.
Budget overshoot is explicit; unknown consumption cannot count toward
within-budget paired rubric results. Report completion for the full
cohort, critical quality regressions and per-pair cost deltas; missing
cost is null. Neither config readiness nor relative performance is
promoted to automatic routing authority.

## Operator acceptance

Use actual pre-decision files and original references, not handoff summaries
with hindsight. Export small batches of cases locally; the CLI bounds JSON
file sizes. Keep historical input and later adjudication separate. Start
with cases covering method invalidity, true negative, mixed results,
unknown evidence, technical failures and authorization blocks. Do not
upload private manifests to GitHub. Run only independently authorized
real provider comparisons. Synthetic tests validate the evaluator, not
the user's historical cases or the effectiveness of Experience.
