# M2-A — bounded Codex to Claude Code review

## Scope and status

This pilot uses only the fixed, hash-checked public synthetic sensor example.
It does not open real research projects, verify scientific claims, grant H6
scope, or enable general Agent routing. The upstream PD-RW-Agent currently
does not supply an independently authenticated original author grant.
This implementation deliberately does not create a parallel authorization
ledger. Original project scope remains authoritative.

## Acceptance steps (operator-controlled isolated environment)

Install the package and compatible, trusted native provider executables.
Configure a private runtime directory outside the repo and real research roots.
First complete the documented, explicitly authorized Codex pilot. Its current
lifecycle and receipt must show successful direct-child exit and matching
structured output bytes. Old receipts with no lifecycle cannot be retroactively
accepted for relay.

~~~powershell
pdrw-orch relay probe
pdrw-orch relay preview --plan-id pilot-001 --attempt-id attempt-001
~~~

The preview returns the exact second-provider prompt and its SHA-256, the
selected source line numbers, the proposed specialist and stable second task.
Review the prompt, including selected local Policy text. No original report
free text, arbitrary paths, plan IDs or report hashes are transmitted to
Claude by the constructed prompt. The Policy text is transmitted, so verify
it is appropriate for the external provider.

Only when expressly willing to incur a second provider call in an isolated
environment, use that preview digest:

~~~powershell
pdrw-orch relay run --plan-id pilot-001 --attempt-id attempt-001 --approved-prompt-sha256 REVIEWED_PROMPT_SHA256 --execute --ack-external-model
pdrw-orch relay inspect --plan-id pilot-001 --attempt-id attempt-001
~~~

IDs above are placeholders; use the actual Codex pilot IDs. To specify a
native Claude executable add `--claude-bin PATH` to probe or run.
Probe checks CLI help and version only, not credentials or readiness.
The adapter needs compatible flags documented in
https://code.claude.com/docs/en/cli-reference including `--safe-mode`,
`--tools ""`, `--strict-mcp-config`, `--no-session-persistence`,
`--permission-mode dontAsk`, `--no-chrome`, JSON-schema output,
`--max-turns 3` and `--max-budget-usd 0.50`.
Those flags are requested controls, not proof of OS containment or actual
charges; provider behavior and flags must be verified on the operator host.
Temporary files are used for output and bounded reads; this is not a hard
disk quota. An actual model call may consume quota or incur charges.
CI does not invoke either provider.

## Relay semantics

- Check the exact existing SQLite intent, original synthetic Codex contract,
  final local receipt and child lifecycle. Accept only matching output bytes
  and successful child exit. Verify fixed response schema and public code.
- Extract only well-formed, in-range synthetic code line references, deduplicate
  and sort them. No arbitrary previous Agent claims are forwarded. If no
  valid references exist, the second review considers the whole fixed fixture.
- Prepare a distinct independent-review task with current applicable Policy.
  Confirm the reviewed prompt hash before provider probe/reservation. A stable
  second task attempt is reserved at most once; no automatic re-run.
- Record child launch/exit and receipt. Reconcile exact parent and child
  artifacts, provider identity and return code, normalize the second report
  as untrusted Agent output, then create a private ChatGPT handoff.
- A completed second review stops at REVIEW_OUTCOME_PENDING, not another
  automatic model call. A failure or unresolved process does not authorize
  retry. No general real-project routing or paid model authentication is
  inferred. Cross-provider handoff is deterministic within this pilot scope.

The historical output basename codex-final.json is retained inside each
attempt directory for compatibility with the existing receipt reader. Provider
identity and version are recorded separately.

## Remaining acceptance

Run a real Codex and Claude Code pair on an isolated operator workstation,
inspect actual provider credential/CLI behavior, compare independent review
quality and measured resource consumption, and verify the original PD-RW
authority/host operation binding before any real research integration.
Local consistency is not authentication of all files or scientific validity.
