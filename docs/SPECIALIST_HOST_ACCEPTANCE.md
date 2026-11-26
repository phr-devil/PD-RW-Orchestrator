# Run the existing specialist workflow in the actual research host

Status: implementation and offline CI are not live acceptance. This is one
operator task for WorkBuddy/Codex; do not build another scheduler, approval
store, mock agent, benchmark dataset, or repeat already successful checks.
Use the existing PD-RW original workflow, original H3/H4/H6/H8 decisions,
local permissions and evidence. The instructions below grant no new effects.

## Start with what is actually installed

Read SPECIALIST_INTEGRATION.md once, then inspect the actual local checkout,
Python environments, executables, selected pinned source bytes, dependencies,
Docker/Conda availability, allowed network/model/data scope and resource
limits. Reuse valid installed environments. Do not auto-update the frozen
Agent RC, install additional packages, pull images, download datasets, send
private data externally or call paid models without the applicable authority.
When a permission is missing, report the precise remaining grant and proceed
with unrelated permitted checks. Never simulate an accepted provider.

## One bounded host acceptance task

- ToolUniverse: if its pinned package is installed and public egress is
  authorized, run the documented public Crossref query and one Zenodo
  metadata query. Check DOI/record metadata against actual source records.
  No file downloads or LLM calls. Use a fresh attempt root per lookup.
- ARC: run only the approved public-topic stage 1–4 path, with actual
  reviewed config, bounded budget and no automatic publishing, writing or
  experiments. Preserve actual outputs and verify search did not degrade
  into placeholders. Do not launch if startup effects cannot be contained.
- AIDE and RD-Agent: if authorized, use their existing shared grouped
  synthetic pilot (one attempt per provider first). Collect native code,
  logs, actual exit/usage and selected candidate. Replay exact selected code
  independently with no access to reference truth or provider credentials;
  score through the existing common evaluator. Keep original predictions
  distinct from independent replay predictions. For RD-Agent preserve all
  required code modules, not only main.py. Use an independent review
  environment; public fixture results are engineering evidence only.
- After the engineering gates and genuine original research authorization,
  choose one existing task with fixed DEV protocol and a real decision to
  make. Prepare AIDE or RD-Agent custom DEV snapshot using the shared manifest,
  and compare the candidate to existing valid strong baseline/evidence.
  Avoid launching both unless the alternative can change the scientific
  decision within the allowed budget. No SEALED, new downloads, writing or
  scope expansion without separate authority.

Use existing compile/prepare/collect/advise --intake-root interfaces. If
a prior outcome was independently reviewed, use specialists compile with
the actual review reference and prior intake/root for the next explicit
task. A byte check or declaration is not a verified author decision.
Resolve original evidence once; do not send the same result for repeated
independent review merely because a provider changes. The current host
is responsible for native execution, permissions and containment. No
automatic dispatch is required for v1.0 operator use.

## Return only decision-relevant evidence

For each attempted provider return: pinned revision and actual environment,
task/attempt ID, native exit status or exact blocker, original artifact
references/hashes, actual usage/time if measured, independent assessment,
and one next action. Keep these fields separate: installed/source match,
native execution observed, scientific evidence valid, scientific outcome
(valid positive/negative/inconclusive/invalid/not-run), cost and human
interventions. UNKNOWN remains UNKNOWN. For true DEV, include original
protocol/Run/review references and closest prior work; never fabricate
original Run IDs from adapter output.

For the next development decision, identify only failures that blocked a
real task, missing scientific capabilities, and credible efficiency gains.
Do not add a new architectural layer for hypothetical future needs.
Report results through existing ChatGPT handoff and, only where actual
evidence supports it, existing Experience feedback. Do not write a paper.

## Native offline CI evidence

The separate `Specialist native contract` workflow checks pinned upstream AIDE config/workspace and actual fixed-code interpreter execution, and ToolUniverse Crossref/Zenodo request construction and response parsing with HTTP intercepted. It uses minimal test dependencies and no research dataset, model, or live service. These results are narrower than full install or real research acceptance. AIDE handoff requests PYTHONUTF8=1 for its native text reader. ToolUniverse uses the upstream light-import mode by default and disables ambient requests proxy/netrc discovery; the approved host must provide a direct permitted connection. Do not bypass this with an unreviewed proxy.

## Actual installation boundaries

Use dedicated environments rather than installing every upstream in the Orchestrator interpreter. Pinned AIDE requires jsonschema==4.19.2 and NumPy==1.26.2, while Orchestrator requires jsonschema>=4.21 and pinned ToolUniverse requires NumPy>=2.2. These are real dependency conflicts, not a reason to upgrade or downgrade the original research environment. Start with Python 3.11 for the provider-specific environments; use the existing host to invoke the selected executable and maintain its isolation. ToolUniverse's native query must run in an environment that can import both Orchestrator and the approved ToolUniverse source. AIDE and RD-Agent native subprocesses do not require Orchestrator in their environments. RD-Agent still requires the approved native Docker/Conda backend and model credentials; the offline settings test does not establish either.

Use examples/arc-discovery.config.example.yaml as a starting config for a fresh ARC attempt, replace approved model/endpoint, hash the reviewed exact bytes and never embed API keys (ARC copies the YAML into run output). ARC's paper target is a per-query/daily declaration, not a total request cap. The host handoff rejects selected unsafe YAML defaults; inspect remaining settings and actual startup hooks in the native host. Local KB remains a disposable attempt-local directory, not an external memory service.
