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
