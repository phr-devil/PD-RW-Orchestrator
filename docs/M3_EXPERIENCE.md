# M3-A — outcome-sensitive planning and local Experience retrieval

## Responsibilities

Orchestrator coordinates task transitions and retrieves scoped advice.
PD-RW-Experience remains responsible for case distillation (ACE), lesson
review, visibility, signed receipts and source verification. PD-RW and
original project records remain authoritative for science and author scope.
No new case library, duplicate research ledger or automatic rule promotion
is introduced.

## Dynamic research decisions

Agent result v2 optionally accepts scientific_assessment.outcome:
POSITIVE, NEGATIVE, MIXED, INCONCLUSIVE, INVALID or NOT_ASSESSED (default).
This is a self-report, not a verdict. Protocol INVALID takes precedence over
a purported gain or negative when focusing independent review. Positive
reports require matched baselines and decisive missing evidence; negative
reports require validity/power checks and narrower-claim assessment; mixed
reports require reproducible boundary conditions; inconclusive reports need
a minimal discriminating check. Engineering failure remains a planning
failure, not a scientific negative. Original-source blockers, authorization
checks and the stop after a completed review are unchanged. No topic/Claim
change, new training, manuscript work or automatic dispatch is authorized.

## Operator configuration (private, outside Git)

Install the trusted PD-RW-Experience package version 0.2.0a1 in an operator
selected Python environment. The integration contract CI checks against
the upstream commit 6f22e958233e1313171f4a6317642e0390445d10. The version
check in the local command is not a full installed-revision authentication.

Create an operator-owned JSON config with exactly these fields; all paths
must be absolute. Use the host-pinned public reviewer key and authorized
source index/root, never a key supplied by an Agent.

~~~json
{
  "schema_version": "1.0",
  "python": "D:\\private\\experience-env\\Scripts\\python.exe",
  "lessons": "D:\\private\\experience\\lessons.json",
  "cases": "D:\\private\\experience\\cases.json",
  "receipts": "D:\\trusted\\lesson-receipts.json",
  "trusted_public_key": "D:\\trusted\\reviewer.pub.pem",
  "public_key_sha256": "REPLACE_WITH_INDEPENDENTLY_KNOWN_64_LOWERCASE_HEX_DIGEST",
  "source_root": "D:\\trusted\\sources",
  "source_index": "D:\\trusted\\source-index.json"
}
~~~

The config is a host input, not an authentication mechanism. A party that
controls both the config and key can replace both. Only the operator may
select these paths and pin the trusted reviewer key. The source root must
not include unauthorized protected data. Do not commit this config or
private catalogs, source paths, signing keys or original research files.

~~~powershell
pdrw-orch advise --task-file TASK.json --result-file RESULT.json --experience-config "D:\private\experience-config.json" --experience-query "leakage prefix baseline" --experience-as-of 2026-11-21 --save
~~~

Use the actual original task visibility cutoff, not today's date for a
historical evaluation. All three Experience options are required together.
Search terms are explicit operator input, not free-form Agent result text.
Without these options the old advise behavior is unchanged.

## Bounded integration and failure semantics

- Retrieve once, only for INDEPENDENT_REVIEW or REVISE_PLAN, and only for
  the proposed next task type. Skip source reconciliation, scope review
  and human-assessment stops. No duplicate retrieval for the previous task.
- Use the installed provider's read-only retrieve entry point in isolated
  Python mode; no ACE execution, feedback mutation, provider/model call
  requested, data download or external API. Trust the selected local
  interpreter/package; Python isolation is not an OS security sandbox.
- Pin the configured key's bytes and check bounded input catalog hashes
  before/after the call. This detects sampled configuration drift, not an
  atomic snapshot of every source file. The provider performs its own source
  byte and signature checks. Orchestrator does not independently attest
  the provider, scientific truth, source equivalence or author permission.
- Request at most three lessons, a 30-second subprocess timeout and a
  32 KiB reply read bound. Do not interpret a timeout as a science result.
  Temporary output is not a hard disk quota.
- Require exact P4 advisory fields, source provenance, unique IDs, matching
  next task type and bounded text/conditions/evidence. Reject attempted
  authority escalation or conflicts with local rule IDs. Keep provider rank
  within P4 while local requirements/must-consider/recommendations retain
  priority under the existing eight-item guidance limit.
- Include selected advice, unverified conditions, source refs and provenance
  in the next instruction and private ChatGPT handoff. Record response and
  catalog fingerprints, requested cutoff and selected IDs. The upstream
  export does not have a separate limitations field; do not infer omitted
  limitations or generalize advice beyond its conditions.
- EXPERIENCE_NO_MATCH means no eligible lessons returned by upstream,
  not proof no relevant case exists: upstream may exclude unsigned, future,
  conflicting, changed or non-public sources. Provider blocked, malformed
  reply, oversize, config drift and timeout remain separate. Base policy
  and advisory planning continue even when optional retrieval fails.

## Acceptance and next gate

Cross-repository CI installs the pinned actual Experience revision and
uses a synthetic Ed25519 signature and matching source bytes. It checks
eligible advice, historical cutoff and rejection after source modification.
Other CI jobs verify offline behavior, ranking, escalation rejection,
catalog drift, and next-task-only selection. No paid model or real research
project is accessed. This tests integration, not whether Experience improves
publication outcomes, and does not activate ACE learning on real cases.

Next: evaluate retrieval with an operator-reviewed case library (without
automatic training), compare decision quality/cost with and without advice,
and carry reviewed feedback to Experience through its existing contract.
Actual author scope, general Agent dispatch and real provider/host validation
are still pending.


## M3-B (v0.9.1): applicability, feedback and matched evaluation

### Conditional transfer screening

The optional --experience-applicability JSON is operator-owned, not an
Agent decision. Bind it to the proposed task ID, project ID and exact
rule SHA-256 printed in experience_retrieval.applicability_screen.
For example (illustrative identifiers):

~~~json
{"schema_version":"1.0","project_id":"P","task_id":"NEXT-T",
 "assessments":[{"rule_id":"L1:v2","rule_sha256":"COPY_FROM_HANDOFF",
 "conditions":[{"condition":"Prefix-visible prediction",
 "status":"MISMATCH","evidence_refs":["original-protocol-ref"]}]}]}
~~~

Use exact exported condition text and include every condition. MATCH or
MISMATCH requires original evidence references; UNKNOWN can omit them.
An exact declared mismatch excludes the advice. Missing, changed or
incomplete judgments leave it review-only, never a verified match.
A declared MATCH still needs scientific confirmation. Optional screening
does not change the underlying decision, grant permission, require a new
author decision or mandate routine re-retrieval. The next agent is explicitly
asked to check conditions and not infer a failed Claim from a historical lesson.

### Feedback candidate

~~~powershell
pdrw-orch experience feedback --handoff HANDOFF.json --assessment ASSESSMENT.json
~~~

Supply the selected rule ID and digest, original proposal identity, and
actual usage declaration, with references to the original new evidence:

~~~json
{"schema_version":"1.0","project_id":"P","task_id":"NEXT-T",
 "rule_id":"L1:v2","rule_sha256":"COPY_FROM_HANDOFF",
 "observed_at":"2026-11-22","science":"NEGATIVE","engineering":"COMPLETED",
 "transfer":"HELPFUL","usage":"APPLIED",
 "observation":"The cheaper test resolved the premise.",
 "evidence_refs":["original-run-ref"]}
~~~

Science is POSITIVE/NEGATIVE/MIXED/INCONCLUSIVE/INVALID/UNKNOWN.
Engineering is COMPLETED/FAILED/UNKNOWN; transfer is HELPFUL/HARMFUL/
NO_EFFECT/UNKNOWN; usage is APPLIED/NOT_APPLIED/UNKNOWN. They are
independent declarations, not verified facts. A valid negative experiment
may be helpful. Failed engineering, unverified usage or inconclusive/
invalid science cannot produce directional lesson feedback. Bind the
candidate to the prior handoff and lesson version; the proposal ID is
not proof of actual execution. The upstream feedback v1 object is nested
under feedback, ready for explicit operator review and separate
pdrw-exp feedback-check. That command returns RECEIVED_UNVERIFIED.
No lesson mutation, automatic training, sign-off, or rule promotion.

### Matched evaluation

Add --experience-ablation to advise with the existing Experience options
to prepare two draft instructions from one common context and one retrieval.
The common-context digest and both instruction digests are provided; the
character delta is not token usage. No model is called. A lack of selected
advice is not a treatment or evidence of zero effect.

After independently executing only already authorized comparisons, supply
a paired manifest to pdrw-orch experience evaluate --assessment PAIRS.json.
Each case must have a common protocol SHA-256 and two distinct result
references. The protocol should freeze model/version, task and evidence,
budget, evaluation rubric and review setup before either arm. Example:

~~~json
{"schema_version":"1.0","pairs":[{
 "case_id":"C1","protocol_sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
 "without_experience":{"protocol_sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
 "result_ref":"result-A","reviewer_ref":"review-A",
 "rubric":{"source_legality":1,"scientific_validity":1,"decision_relevance":0,"avoids_redundant_work":0},
 "tokens":100,"wall_seconds":5},
 "with_experience":{"protocol_sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
 "result_ref":"result-B","reviewer_ref":"review-B",
 "rubric":{"source_legality":1,"scientific_validity":1,"decision_relevance":1,"avoids_redundant_work":1},
 "tokens":120,"wall_seconds":6}}]}
~~~

Use actual measured total tokens and elapsed seconds, not estimates;
scores are independently reviewed binary rubric entries (1 meets criterion,
0 does not). The command checks declared pairing, not actual protocol
bytes, reviewer independence or measurement authenticity. Critical loss of
source legality or scientific validity is counted separately regardless
of aggregate score or cost savings. Output is descriptive only, never
a causal estimate or proof of publication improvement. Pre-register
representative cases and blinded review, include failed/unknown attempts
rather than dropping them, and use an appropriate paired statistical
analysis for a real efficacy study. The repository does not execute these
experiments, sign feedback or consume paid models.
