# M4-A — evidence-bound research route comparison (v0.10.0)

Orchestrator remains a coordinator, not an independent scientific authority.
The new local routes command compares explicit candidate plans from a prior
advisory handoff. It does not run experiments, choose H8, certify a Claim,
authenticate H6, or dispatch Agents. No new research ledger is created.

## Usage

~~~powershell
pdrw-orch routes --handoff HANDOFF.json
pdrw-orch routes --handoff HANDOFF.json --options OPTIONS.json
~~~

The first command returns the current project/proposal IDs and a canonical
context SHA-256 (including result, decision, proposed task, next guidance and
source context). Use these exact values in an operator-reviewed manifest.
Example only:

~~~json
{
  "schema_version": "1.0",
  "project_id": "P",
  "proposal_id": "NEXT-T",
  "context_sha256": "COPY_FROM_CONTEXT_COMMAND",
  "remaining_budget": {"tokens": 20000, "wall_seconds": 3600},
  "options": [{
    "id": "reuse-existing",
    "route": "REUSE_EVIDENCE",
    "premise": "Existing DEV results can discriminate the proposed mechanism.",
    "evidence_refs": ["original-run-ref", "original-protocol-ref"],
    "discriminating_outcomes": ["Effect survives matched baseline", "Effect disappears"],
    "stop_rule": "Stop after checking the existing matched results.",
    "capability": "review",
    "prerequisite": "SUPPORTED",
    "scope": "EXISTING_SCOPE_DECLARED",
    "decision_value": 3,
    "contribution_potential": 2,
    "tokens": 1000,
    "wall_seconds": 60
  }]
}
~~~

Use actual original evidence references and legitimate scope. The manifest
is an explicit declaration, not a trusted verification of source bytes,
permissions, scores or feasibility. Do not supply private records to remote
providers or commit them to the repo. A changed handoff requires a fresh
context binding, not an automatic repeat of previous research.

## Route comparison semantics

- Routes: REUSE_EVIDENCE, MINIMAL_CHECK, REPAIR_METHOD, CONTINUE_DEV,
  NARROW_CLAIM, PIVOT, HOLD. Each option includes a premise, evidence,
  two to four distinct outcomes, stop rule, and relevant capability.
- Prerequisite: SUPPORTED, UNKNOWN, CONTRADICTED. Unknown or contradicted
  options stay visible but are not ranked. Scope: EXISTING_SCOPE_DECLARED,
  UNKNOWN, NEW_SCOPE. Existing scope is still unverified.
- Decision value and contribution potential are declared ordinal estimates
  (0–3: none, low, medium, high), not predictions or objective measurements.
  Estimated token and wall-second costs are integers or null. Null means
  unknown, never zero. Budget limits are declared separately.
- Preserve original reconciliation, policy and scope blockers. A reported
  invalid method blocks CONTINUE_DEV comparison until reviewed; it does not
  prove the method invalid. NARROW_CLAIM/PIVOT/new scope remain visible as
  options requiring original scope/H8 review, never automatically selected.
- Compare only options with declared supported prerequisites, existing scope,
  complete estimates, and within budget. Pareto dominance means at least as
  good on both scientific value axes, at most as costly on both resource axes,
  and strictly better on at least one axis. Keep all nondominated options;
  do not invent weights, a winner, or a publication probability.
- Capability candidates are non-mock registered Agents whose declared role
  matches the option. An independent review excludes the previous Agent.
  Registry priority orders the list only; it is not measured performance.
  Real provider readiness remains false unless actually verified through a
  trusted host. This module returns no executable recommendation.

Use the frontier to help decide what evidence would change the scientific
decision. Material Claim changes require the original author workflow;
ordinary existing-scope DEV must not be asked for redundant grants simply
because this advisory tool cannot authenticate them.

## Evaluation and cost accounting

The existing experience evaluate command accepts null tokens or wall_seconds
when actual usage is not available. A missing arm measurement produces a
null pair delta and a null overall total for that metric, with measured-pair
counts reported. Scientific quality comparisons remain available. Estimates,
instruction length and missing values must not be reported as measured usage.

Current tests use public synthetic counterexamples: dominated expensive work,
tradeoffs, invalid method vs continued tuning, stale context, unknown
prerequisites, budget overflow, unconnected Agents, original gate preservation,
and missing usage. The existing pinned Experience contract CI remains.
These are regression tests, not historical research efficacy evidence.

## Remaining validation

Use the original, independently reviewed historical project cases on the
operator host. Freeze the original decision time and available evidence,
avoid future-result leakage, compare proposed next actions against an
independent reference assessment and record actual provider usage.
Keep failed and unknown cases in the cohort. Evaluate specialist capability
under matched tasks and budget before changing routing priorities.
Original H6 authorization and real Windows provider acceptance remain
unverified. Do not add more infrastructure solely to simulate these gates.
