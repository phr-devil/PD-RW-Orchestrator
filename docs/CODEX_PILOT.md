# M2-Pilot-001 — First real local Codex CLI adapter (synthetic fixture only)

## Status and trust boundary

This repository now has a **real, opt-in subprocess path** to Codex CLI.
GitHub CI tests the adapter with a fake subprocess. **No claim is made that
Codex is installed, authenticated or has run on the author's Windows machine.**

The pilot is deliberately limited to the public, synthetic fixture in
`examples/codex-pilot/`. It cannot accept a user-supplied research project
root, task objective, source refs, budget escalation, or model-generated shell
arguments. It never invokes Codex on original P19/P42/P54 projects.

`codex exec` supports `--sandbox read-only`, `--output-schema`,
`--output-last-message`, and `--ephemeral`. The adapter additionally uses
`--ignore-user-config` and `--ask-for-approval never`. It does **not** use
`--yolo`, `--add-dir`, `--search`, or elevated sandbox modes.

**Important:** A Codex read-only sandbox is not a strict read-visibility
boundary. Codex can potentially read more than the fixture, and the local
agent may connect to a model provider. To isolate sensitive local files,
execute in a disposable VM/container or separate account with no access to
private data and no project MCP servers. `--ignore-user-config` reduces
config/MCP risk but is not proof of host security.

## Workflow

1. Install Codex CLI separately and authenticate if you intend to make a real
   provider call. Paid/plan usage can apply; the orchestrator cannot cap
   internal model tokens or API spend.
2. Install this package from a trusted local checkout, ideally in a clean
   virtual environment (`python -m pip install -e ".[dev]"`).
3. Set a **private absolute** `PDRW_ORCH_RUNTIME_DIR` outside every research
   project, the Orchestrator checkout, PD-RW, and case sources.
4. Run `pdrw-orch codex probe` — calls only `codex --version` and
   `codex exec --help`; no model call.
5. On a disposable environment with only the synthetic fixture, explicitly
   invoke the real pilot:

~~~powershell
$env:PDRW_ORCH_RUNTIME_DIR = "D:\\private-orchestrator-runtime"
pdrw-orch codex probe --codex-bin "D:\\tools\\codex.exe"
pdrw-orch codex pilot --plan-id m2pilot-001 --attempt-id attempt-001 --codex-bin "D:\\tools\\codex.exe" --execute --ack-external-model
~~~

Use the **native codex.exe** on Windows, not `codex.cmd`/`codex.bat`
(npm shell wrappers can change subprocess argument semantics). Find the native
binary from your installed Codex distribution; paths above are examples only.

`--execute` and `--ack-external-model` are required together. The CLI
never automatically calls a paid model in `doctor`, `agents list`,
`advise`, `demo`, or `codex probe`.

## Output semantics

Before launching Codex, the controller stages the immutable synthetic task
and records `INTENT_UNCERTAIN` in the private SQLite store. The process is
attempted **once**; after a crash/timeout no automatic retry is permitted.
The operator must reconcile external process state before any new attempt.

A successful CLI exit + schema-valid final JSON produces an untrusted v2 Agent
Result, conservative next action, and private `handoff.json/md`. This is a
real subprocess result, **not** a verified scientific result. Failure and
timeout states remain explicitly unresolved. Results are not automatically
fed back as PD-RW scientific Runs.

Current limits: one built-in synthetic task, one attempt per plan, 120-second
wall-clock timeout, structured output capped at 64 KiB, no real user data,
no write-enabled Agent, no automatic second-Agent dispatch. Token or monetary
budget is **not** enforced; the real provider may incur charges.

## Acceptance

- CI: probe and actual CLI subprocess call are simulated using a synthetic
  runner. The test asserts the exact read-only flags, zero model invocation
  without opt-in, plan persistence, no repeat, normalized results and no
  scientific authority escalation.
- Operator acceptance (pending): run the above on an isolated Windows machine
  with a real installed/authenticated native Codex executable. Compare the
  resulting JSON and Markdown with the fixture, verify the no-edit behavior,
  and inspect provider usage in the authenticated Codex account.

Upstream specification:
[Codex CLI reference](https://learn.chatgpt.com/docs/cli/reference),
[non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode).
