# Agent adapter contract

Agent providers are distinct processes/environments and must remain optional. **Current v0.1 implements mock only.** Configured `arc`, `rdagent`, `aide`, `host` entries are NOT_CONNECTED until an actual provider handshake and bounded acceptance succeed.

Interface: `run(TaskPacket, GuidancePacket) -> ResultPacket`. Must carry project identity, task IDs, effect intents, source refs, model/tool budgets, state of execution, output refs, limits and uncertainties. No adapter may make science truth from a model-generated summary.

Recommended priority: first connect host WorkBuddy/Codex (where actually supported), then a live AIDE code task, and optionally ARC/R&D-Agent after environment readiness. Agent capability is selected by Task, not fixed workflow order. Isolate providers' Python environments; avoid merging dependency graphs.

Before enabling effects, implement and test a **trusted host adapter**, authenticated effect approval, filesystem + network restrictions, process cancellation and durable reconciliation. No config `ready: true`, YAML permit or SHA token can replace these controls. Never interpolate untrusted Task content into shell commands.

Require health check, version pin, handshake, explicit capability map, input/output schema contract, timeout, cancelled attempt receipt, bounded retries, and rollback. Demo adapter is not a proxy for measured external performance.
