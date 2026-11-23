# Agent adapter contract

Agent providers are distinct processes/environments and must remain optional. **Current v0.4 implements mock plus one explicitly invoked synthetic-fixture Codex subprocess.** Configured `arc`, `rdagent`, `aide`, `host` entries are NOT_CONNECTED until an actual provider handshake and bounded acceptance succeed.

Interface: `run(TaskPacket, GuidancePacket) -> ResultPacket`. Must carry project identity, task IDs, effect intents, source refs, model/tool budgets, state of execution, output refs, limits and uncertainties. No adapter may make science truth from a model-generated summary.

Recommended priority: first connect host WorkBuddy/Codex (where actually supported), then a live AIDE code task, and optionally ARC/R&D-Agent after environment readiness. Agent capability is selected by Task, not fixed workflow order. Isolate providers' Python environments; avoid merging dependency graphs.

Before enabling effects, implement and test a **trusted host adapter**, authenticated effect approval, filesystem + network restrictions, process cancellation and durable reconciliation. No config `ready: true`, YAML permit or SHA token can replace these controls. Never interpolate untrusted Task content into shell commands.

Require health check, version pin, handshake, explicit capability map, input/output schema contract, timeout, cancelled attempt receipt, bounded retries, and rollback. Demo adapter is not a proxy for measured external performance.

## Codex pilot adapter

`pdrw-orch codex probe` inspects actual native executable flags without a
model call. `codex pilot` is a separately opt-in path that only reads the
synthetic fixture, reserves a one-time intent and requires an external-model
acknowledgment; it never marks the registry agent ready for general routing.

No paid model invocation is made by GitHub CI. This is **not yet a general
host adapter** for private research projects or write-enabled DEV. For actual
isolation use host/VM resource restrictions and validated permissions; a Codex
`--sandbox read-only` flag is not equivalent to an access-control boundary.
See [CODEX_PILOT.md](CODEX_PILOT.md).
