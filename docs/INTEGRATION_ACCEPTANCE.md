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
   and disjoint private Orchestrator runtime directory.
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
