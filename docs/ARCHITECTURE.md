# Architecture: orchestrate, do not re-govern

**Status:** v0.1 runnable dry-run foundation. No live external-agent invocation.

The six orchestration capabilities are `planner`, `router`, `adapters`, `handoff`, `controller`, and `review`. `policy` is an additional cross-cutting guidance system; `registry` and `integrations` are small shared services.

## Authority and data ownership

1. Original author instructions and authenticated host grants are authoritative for effects.
2. PD-RW owns scientific policy, H1–H10 decisions, experiment isolation and writing rules.
3. The project's original STATE/RESEARCH_RECORD/protocols/Run artifacts own science evidence.
4. PD-RW-Agent provides evidence-aware retrieval and limited checks; its tool output is not scientific truth.
5. Orchestrator owns ephemeral operational task planning, routing, attempt receipts and adapter I/O.
6. PD-RW-Experience owns derivative advice, never source cases or permissions.

Never create a parallel scientific ledger, automatic H-stage, evidence-verdict engine or new project-identity authority.

## Task flow

Host request -> original project identity & scope -> applicable policy references -> DAG -> capability registry -> healthy allowed adapter -> task execution -> structured result refs -> optional independent review -> handoff / next task.

In v0.1 only **mock** capability slots are runnable. Side effects are always rejected at the local orchestrator level; a future trusted host security integration must authenticate and restrict the real operation before this changes. A path and a string named APPROVED are never such proof.

- **Planner:** bounded dependency graph, no mandatory linear ARC/R&D/AIDE pipeline.
- **Router:** eligible capabilities and verified readiness, never an advertised benchmark score.
- **Adapters:** one interface per provider, no cross-environment imports or shell-string execution.
- **Handoff:** minimal refs, statuses and uncertainty; never stale chat history as evidence.
- **Controller:** no retry of uncertain non-idempotent jobs, no recursive subagent delegation.
- **Review:** mechanical coherence tests now; actual scientific check is an external PD-RW/host capability.

## Failure semantics

Treat execution status, evidence validity, hypothesis outcome and publication readiness as *separate axes*. `DEMO_ONLY` is never `VALID_POS`. `BLOCKED_AUTH` halts only effect-bearing tasks. `NOT_CONNECTED` is not `FAILED_SCIENCE`. A missing or ambiguous source remains UNKNOWN.

Future persistence must use task_id + attempt_id + idempotency key and reconcile process state before any retry; do not persist project-scientific claims in operation receipts.

## External project alignment

[PD-RW-Agent RC architecture](https://github.com/phr-devil/PD-RW-Agent/blob/rc/v1.0-integration/docs/ARCHITECTURE.md). The RC is v1.0.0rc1 and not merged into its default branch as checked; pin the actual git SHA and verify adapter compatibility. Current tests do **not** prove improved scientific performance.
