# v0.3 Task transition contract

- `decide_next` returns **v1.1** candidate decision with a distinct `NextTaskProposal` (v1). This is not a `TaskPacket` approved for execution.
- The proposal's goal, role and task type are **new**. Previous budget, side-effect intents and authorization refs are context only; new task has **no effects and no inherited grant**.
- The CLI `advise` compiles Policy for the proposed task separately from prior task. This avoids feeding code-development rules as binding instructions to a scientific reviewer.
- `VERIFY_EXISTING_SCOPE` distinguishes a missing host permission check from truly needing a **new** author decision. Only original source/host can determine whether H6 already covers the work. No JSON flag may declare verified grant.
- `advise --with-pdrw [--python PATH]` is opt-in; it calls the single read-only upstream `resume` bridge and incorporates source status as blockers or science-review prompts. Without `--with-pdrw`, the output is explicitly an unverified advisory.
- `RECONCILE` and `INDEPENDENT_REVIEW` are still proposals; a real agent has not been selected or dispatched.
- Previous ResultPacket v1 remains accepted; normalized Agent v2 is unchanged. The decision schema is upgraded from v1.0 to v1.1. The bundle schema changes from v1.0 to v1.1 and keeps `guidance` (old-task guidance) for compatibility, while adding `next_task` and `next_guidance`.
- No automatic manuscript actions, SEALED access, LLM inference, training or external uploads. Store no real unpublished project data in this public repository.

## Example

~~~powershell
pdrw-orch advise --task-file examples/decision-task.example.json --result-file examples/agent-result-v2.example.json
# After configuring PDRW-Agent RC locally, optionally:
pdrw-orch advise --task-file examples/decision-task.example.json --result-file examples/agent-result-v2.example.json --with-pdrw
~~~

Acceptance next: original project receipt/identity correlation, trusted review of dependencies, then a real read-only specialist adapter.
