# Specialist-first integration

Orchestrator selects, adapts and composes existing research systems. It does
not duplicate PD-RW-Agent's general-host Skill, scientific checks, original
source evidence and project recovery, or Experience's lesson distillation.
PD-RW and original author/project/host remain authoritative. Do not implement
another scheduler or search algorithm when an existing system suffices.

## Pinned screening snapshot (2026-11-26)

| Project | Initial fit | Actual status |
|---|---|---|
| WecoAI/aideml | Native ML code tree search | Preview and artifact intake, no live execution |
| microsoft/RD-Agent | Scenario-specific research/development iteration | Native synthetic task preparation/intake, no live execution |
| aiming-lab/AutoResearchClaw | Literature, hypothesis, staged pipeline | Stages 1–4 preview/intake only |

The catalog includes commit, observed stars, declared license, source paths,
and limitations. Stars are not a scientific ranking. Other discovery leads:
SakanaAI/AI-Scientist-v2 (96bd51617cfdbb494a9fc283af00fe090edfae48;
license status requires review) and sjtu-sai-agents/ML-Master
(d55311af2a3a9038952a31b8ca6d7771454f54ce; license not established).
Only repository metadata was checked for these two; not accepted candidates.
Expand after the first real pilot, not by adding speculative adapters.

## First adapter: AIDE

Reviewed the pinned upstream README, setup.py (aideml 0.2.2),
aide/utils/config.yaml, aide/utils/config.py and aide/run.py. AIDE owns its
native tree search, iteration and candidate code generation. No reimplementation.
Use a separate environment fixed to the inspected revision; installation is
not performed by Orchestrator.

~~~powershell
pdrw-orch specialists list
pdrw-orch specialists select --capability optimization
pdrw-orch aide preview --plan-file examples/aide-dev-preview.example.json
~~~

The example contains placeholder models, protocol and manifest; never treat
it as ready to execute. Preview returns native argv, task.md bytes/digest,
declared plan identity and required host checks, but never writes files,
runs a subprocess, authenticates a grant or proves installed version.
Task text is intentionally separate from argv. The operator must ensure the
actual fixed evaluator and group/temporal DEV split are independently enforced;
turning off AIDE's generic CV does not implement a scientific evaluator.
The default data preview and report generation are disabled; generated code
or execution feedback may still expose data. Step count, per-program timeout
and output-token request are not hard total model/compute/cost limits.

**Next live acceptance, only with separate authorization:** prepare one fresh
disposable isolated environment, public synthetic DEV-only snapshot, exact
task/protocol, approved provider/model/cost and independent evaluator.
Validate the pinned install, actual task/manifest bytes, process-tree and
resource/egress limits. Do not mount private projects, reserved data,
credentials usable by generated code, or shared writable host paths.
The operator-controlled trusted host must authorize and launch the reviewed
native command; this adapter intentionally has no execute flag.

The upstream prefixes the experiment name with a numeric index and writes
best_solution.py and journal.json under logs/<index>-<attempt_id>. After an
operator-authorized attempt, intake exact output files without running them:

~~~powershell
pdrw-orch aide collect --plan-file PLAN.json --attempt-root ABSOLUTE_ISOLATED_ATTEMPT_ROOT --run-name 0-attempt-001
~~~

Intake hashes bounded output bytes and emits an untrusted v2 agent_result for
the existing advise interface. Extract that nested object to a private result
file and use the corresponding TaskPacket with the same project/task IDs.
Refs are relative to the attempt root, not original scientific Runs. Byte
observation does not bind a process, provenance, authorization or plan.
No automatic copy, registration, retry or downstream dispatch. Review the
candidate code, original protocol, independent predictions and strong baseline
using existing PD-RW tools before accepting a contribution. The host must
ensure immutable isolated outputs; intake does not prove OS-level containment.

## Fixed public synthetic acceptance task

Use a fresh absolute root on the operator machine. The new command only creates
deterministic public synthetic files; it never imports/starts AIDE or calls a
model. Set actual approved provider/model names (the placeholders below are
not an authorization).

~~~powershell
pdrw-orch aide-pilot prepare --root ABSOLUTE_NEW_PILOT_ROOT --attempt-id pilot-001 --code-provider openai --code-model MODEL --feedback-provider openai --feedback-model MODEL
pdrw-orch aide-pilot verify --root ABSOLUTE_NEW_PILOT_ROOT
~~~

The worker directory contains only task.md and labeled train (6 groups),
validation (2 groups) and unlabeled test (4 groups), 12 rows per group. Only x
is a legal feature; group and row IDs are not predictors. The review directory
contains the exact plan and manifest and must not be mounted to the worker.
The evaluator derives test labels in the operator/review process from the
public fixture generator. This is not a confidential blind test or a genuine
scientific benchmark; the source is public and must not be available to the
worker. Verification checks exact file set and bytes, not host isolation.

The returned native argv must be invoked from worker/ in a separate trusted
environment at the pinned revision, only after real permission, total cost,
egress, time and process-tree controls have been established. Do not pass
raw model keys to generated code. AIDE internally parses reported validation
metrics with an LLM, and save_run can select even a buggy node. Its latest
workspace submission is not necessarily from the selected best code.
After inspecting/collecting the selected code, a trusted operator must replay
that exact code on the frozen worker inputs in a fresh isolated environment,
then explicitly export its predictions to review/submission.csv with columns
row_id,prediction. Record the actual code hash, run and prediction provenance
separately; do not overwrite the original provider output.

~~~powershell
pdrw-orch aide-pilot score --root ABSOLUTE_NEW_PILOT_ROOT
~~~

Scoring independently recomputes RMSE and per-group values against the fixed
test labels and train-only mean/linear baselines; it rejects duplicate,
missing, foreign or non-finite predictions and tampered inputs. It never
executes candidate code, authenticates prediction origin, or declares valid
science. Compare the general-host route using a separately prepared identical
fixture and the same evaluator. The public synthetic holdback is not SEALED
project data. No scientific superiority is inferred from this engineering
pilot; real matched independent research evaluation remains necessary.

## Read-only installation check

~~~powershell
pdrw-orch aide-install --root ABSOLUTE_PACKAGE_PARENT
~~~

Supply the actual site-packages parent (non-editable) or checkout parent of
the aide package (editable). Compare six specific source/config files with
the Git blob IDs retrieved at the pinned revision. CRLF conversion or
packaging differences may legitimately fail exact byte equality. No package
import, subprocess, installation, API or credential access occurs. A match
does not authenticate the interpreter, executable, entire dependency closure,
installed commit or capability. Resolve any mismatch before the real pilot.

## Complementary discovery: AutoResearchClaw

At pinned source, native CLI supports --from-stage and --to-stage. Restrict
the first discovery to TOPIC_INIT through LITERATURE_COLLECT (1–4), before
LITERATURE_SCREEN (5), experiment design (9), code generation (10), and
paper writing (16–17). Do not auto-approve, resume, or expose other stages.
The plan is public topic, scope, declared paper target and approved config
digest; the paper target is a declaration, not a hard upstream limit.

~~~powershell
pdrw-orch arc preview --plan-file examples/arc-discovery-preview.example.json
pdrw-orch arc collect --plan-file ARC_PLAN.json --run-root ABSOLUTE_ARC_RUN
~~~

No automatic config generation or execution. Upstream stage 1 performs
hardware detection and can try to install torch in sandbox mode; use simulated
mode, no remote/GPU resources. Startup performs model preflight and can
copy config into output; do not store literal credentials in config. Disable
external KB and MetaClaw; review post-pipeline packaging and hooks even with
stage ceiling. Restrict network and filesystem on the trusted host. Model
and literature queries need explicit authorization. The preview cannot
enforce config, paper target, provider spend, or effect isolation.

Intake checks expected artifact files and reported four-stage completion,
rejects visible later-stage directories and inconsistent candidate counts.
A reported real search or unmarked candidate does not prove source existence;
upstream stage 4 has placeholder and LLM fallback paths. No config digest
binding or process provenance is inferred. Return raw untrusted result for
independent literature verification and H3 candidate review, not a claim
of novelty or actual author decision. The caller must confirm the source
and run context; absence of later-stage files is not proof of no effects.

## Complementary algorithm development: RD-Agent

Pinned upstream custom DataScienceScen reads a competition directory, can
reuse a prepared sample directory, and runs main.py in its configured
environment with workspace_input mounted. Its native TestEval explicitly
injects submission_test.csv into the generated-code workspace. Therefore the
public grouped pilot uses the exact AIDE train/validation/test inputs, an
explicit description, a format-only sample submission and identical
pre-created sample data, with **no eval dataset or final answer file**.
Independent scoring reuses the existing evaluator, not native test scoring.

~~~powershell
pdrw-orch rdagent-pilot prepare --root ABSOLUTE_NEW_RD_ROOT --attempt-id rd-001 --config-sha256 REVIEWED_PROVIDER_CONFIG_SHA256
pdrw-orch rdagent-pilot verify --root ABSOLUTE_NEW_RD_ROOT
~~~

The command prepares worker/ds_data and review/plan.json, verifies the
exact native input tree and returns the CLI argv and environment overrides.
No execution, installation, credential access, or configuration binding
verification is performed. The digest is a declaration for operator review.
Use a fresh separate environment, actual approved model configuration,
existing trusted Docker or Conda runtime, no image pulls, no generated-code
network, no shared private source or secrets, and a hard external total cost
and process-tree boundary. The returned host path may need remapping inside
the isolated runtime; verify effective DS settings before authorized launch.
RD-Agent's step/loop/timer limits are requests, not a hard host boundary.
Do not run this with Kaggle, MLE-Bench, or an arbitrary checkpoint.

After the authorized run, manually select the actual candidate workspace
using the native trace, preserve all its required modules/config and copy
only reviewed main.py, scores.csv and submission.csv into review/candidate/.
Intake reads/hashes these three exact files, never deserializes native
sessions, never automatically selects a winner, and never runs code:

~~~powershell
pdrw-orch rdagent-pilot collect --root ABSOLUTE_NEW_RD_ROOT
pdrw-orch rdagent-pilot score --root ABSOLUTE_NEW_RD_ROOT
~~~

The score command requires a separate review/submission.csv produced by
independent replay of the full selected code bundle; the intake prediction
is not automatically reused. Same test rows, RMSE, mean/linear baselines
and group breakdown as AIDE. No real code provenance or scientific validity
is inferred. Review source/metrics independently, report actual budgets
and compare against matched general-host/AIDE arms. This is a public
engineering fixture, not a scientific or confidential benchmark.

## Existing-host handoff (use this path for operator acceptance)

After the provider-specific preparation above, use one common interface to
avoid manually reconstructing task/result JSON. Supply the actual source or
site-packages parent for the separately installed pinned provider.

~~~powershell
pdrw-orch specialist-host prepare --provider aide --root ABSOLUTE_PILOT_ROOT --source-root ABSOLUTE_SOURCE_PARENT
pdrw-orch specialist-host prepare --provider rdagent --root ABSOLUTE_RD_ROOT --source-root ABSOLUTE_SOURCE_PARENT
pdrw-orch specialist-host prepare --provider arc --root ABSOLUTE_ARC_WORKER --source-root ABSOLUTE_SOURCE_PARENT --plan-file ARC_PLAN.json
~~~

The RD-Agent worker must contain the approved .env with the declared digest;
ARC uses config.arc.yaml at its worker root with the approved digest. Only
hash equality is checked; it is not validation of settings, permissions,
or environment precedence. Keep these files and packet outputs private.
The AIDE/RD/ARC source observations compare selected Git blob bytes from
their pinned upstream revisions; no import or full install attestation.
A nonzero exit from prepare indicates a concrete preparation blocker.
A zero exit still means HOST_REVIEW_REQUIRED, not permission to execute.

In WorkBuddy/Codex or another trusted local host, read the packet once,
verify effective config, original scope, isolation and total resources.
Review applicable guidance without altering frozen scientific inputs.
Only when the actual host is authorized and contained, invoke the returned
native argv in the specified cwd with reviewed environment overrides.
Use existing host controls, not a new Orchestrator subprocess service.
Preserve exit status, code, logs, actual usage and any unresolved execution.
Do not retry an uncertain attempt. No general real-project DEV dispatch
is enabled by this interface; AIDE and RD use the fixed public pilot only.

After an actual attempt and reviewed export, collect into a private JSON file
(outside the provider worker). Example PowerShell (UTF-8 output):

~~~powershell
pdrw-orch specialist-host collect --provider aide --root ABSOLUTE_PILOT_ROOT --run-name 0-attempt-001 | Set-Content -Encoding utf8 INTAKE.json
pdrw-orch advise --intake-file INTAKE.json
~~~

RD uses --provider rdagent and its prepared root; ARC uses --provider arc,
its worker root and --plan-file ARC_PLAN.json, with output under run/.
No run-name is needed for those providers. The unified intake maps existing
native outputs to the existing TaskPacket and v2 agent result, with refs
relative to the operator-selected attempt root. For an AIDE/RD replay already exported to review/submission.csv, add
--score-replay to collect; the shared independent scorer then contributes
RMSE, reference baselines, prediction digest and per-group errors to the
private intake. For ARC the intake preserves candidate and placeholder counts.
The envelope is untrusted: advise normalizes the task and agent self-report,
checks the structure of artifact references and carries bounded reported
hashes/metrics into the handoff, but does not independently re-open sources
or verify prediction/code provenance. Full group metrics remain in the intake. Use existing --with-pdrw and
Experience options when relevant and actually available. For synthetic
pilots do not invent original project Run IDs. For ARC, independently verify
literature and prepare H3 options; no automatic author choice. If the provider
fails or outputs are missing, use existing manual result status/advise path
with the actual failure or uncertainty; never fabricate a successful intake.

## Additional specialist search (2026-11-26)

See [SPECIALIST_CANDIDATES.md](SPECIALIST_CANDIDATES.md) for a source-pinned
screen of five complementary or overlapping systems. Do not install all;
prioritize actual native use and targeted, missing research capability.

## From fixed engineering pilot to operator-staged DEV

AIDE can now consume an explicitly staged, flat DEV-only snapshot instead of
the fixed synthetic fixture. This does not authorize real-project execution
or data export. The operator must select and stage only already authorized
DEV bytes in a disposable isolated root. Never point this tool at the
original project tree or reserved data.

Layout: ROOT/worker/data/ (flat data files), ROOT/review/manifest.json.
The manifest is an exact list, with SHA-256 and size for each file:

~~~json
{"schema_version":"aide-dev-snapshot-v1","project_id":"P","task_id":"T","scope":"DEV_ONLY_DECLARED","files":[{"name":"train.csv","sha256":"<actual SHA256>","bytes":123}]}
~~~

Use the existing AIDE plan schema with actual project/task IDs and
protocol reference, reviewed goal/evaluation text and SHA-256 of the exact
manifest file bytes. Stage creates only worker/task.md; verify checks
the exact data set, size/hash, task bytes and declared scope. Maximum 64
flat files, 128 MiB/file, 512 MiB total. No copying, original project traversal,
automatic grant or provider call. The operator must supply independent
project-specific evaluator and replay; synthetic scoring is forbidden here.

~~~powershell
pdrw-orch aide-dev stage --root ABSOLUTE_DEV_ROOT --plan-file DEV_PLAN.json
pdrw-orch specialist-host prepare --provider aide --root ABSOLUTE_DEV_ROOT --plan-file DEV_PLAN.json --source-root ABSOLUTE_SOURCE_PARENT
# Existing authorized host runs exact native argv only after real scope/containment checks.
pdrw-orch specialist-host collect --provider aide --root ABSOLUTE_DEV_ROOT --plan-file DEV_PLAN.json --run-name 0-attempt-001
~~~

For preliminary routing:
~~~powershell
pdrw-orch specialists recommend --task-file TASK.json --scope staged_dev
~~~
Scope is declared, not authenticated. Public topics may use ARC discovery,
fixed-metric tasks may use AIDE, synthetic RD iteration may use RD-Agent,
and scientific review defaults to the general host. Denied effects and
zero model-call budgets prevent model-based recommendations. This is a
task-fit suggestion, not runtime acceptance. Do not send private topics,
data, paths, credentials or unapproved instructions to external services.

## Narrow native ToolUniverse literature lookup

For a public bibliographic question use the pinned ToolUniverse Crossref
tool instead of an entire research agent. The optional dependency is
operator-installed in a dedicated environment, not a core dependency.
The implementation calls the upstream CrossrefRESTTool directly with its
pinned config, only keyword search (1–20 results) or a DOI lookup. It
does not load a workspace profile, generic tool catalog, arbitrary endpoints,
LLM or generated code. It compares selected source blobs and checks the
active package origin, not the entire dependency or environment closure.

~~~powershell
pdrw-orch tooluniverse preview --plan-file examples/tooluniverse-public-literature.example.json
# Only in an approved isolated environment, with explicit public network consent:
pdrw-orch tooluniverse query --plan-file PUBLIC_PLAN.json --root ABSOLUTE_NEW_LOOKUP_ROOT --source-root ABSOLUTE_PACKAGE_PARENT --execute --ack-public-network
pdrw-orch tooluniverse collect --plan-file PUBLIC_PLAN.json --root ABSOLUTE_LOOKUP_ROOT
~~~

The query creates a fresh request record and a compact literature.json with
DOI/title/venue/year and reported citation counts; duplicate DOI records are
collapsed and page count is distinct from total matches. No abstracts or full
papers are copied. The returned standard intake can be used by existing
advise --intake-file. Native network retries/timeouts are not hard total limits.
Never put unpublished hypotheses, personal details, credentials or private
research information in public_text. The host must authorize egress to
Crossref and ensure the environment is credential-free and isolated.
An explicit CLI flag is not an original research grant. The local policy
network deny is honored. If the lookup fails, reconcile the existing
request root rather than automatically retry. This is metadata discovery,
not literature completeness, relevance or novelty verification.
No live installation or network execution is claimed by unit tests.

## Compile an actual next task, without hand-rewriting provider plans

Use existing TaskPacket and a small explicit provider-options file. The
compiler delegates to the existing task-fit route and native validation;
private objectives, evidence contents and author grants are not copied into
the provider request. It accepts ARC public discovery, ToolUniverse public
lookup and AIDE operator-staged DEV. Fixed AIDE/RD engineering pilots remain
owned by their existing fixture constructors. Unsupported tasks return the
general-host route or an explicit block.

~~~powershell
pdrw-orch specialists compile --task-file examples/specialist-compile-task.example.json --scope public_topic --options-file examples/specialist-compile-options.example.json --out-plan ABSOLUTE_NEW_PLAN.json
~~~

The optional output is the native plan JSON, not the compilation envelope;
feed it directly to the existing provider-specific commands. It is created
exclusively at the selected absolute path, never overwritten. For ARC the
options are attempt_id, public_topic, research_scope, max_papers, config_sha256.
For AIDE they are the existing plan fields excluding schema_version,
project_id and task_id; protocol_ref must be in the new TaskPacket. For
ToolUniverse the options are attempt_id, operation, public_text, limit.
Choose the next task's scope and explicit provider-facing text locally.
Task-specific guidance and budget remain review inputs; no automatic
execution or inherited permission.

For cross-provider relay, after the prior result has been independently
assessed in the original workflow, provide its intake, immutable attempt
root and a review reference included in the new TaskPacket.evidence_refs:

~~~powershell
pdrw-orch specialists compile --task-file NEXT_TASK.json --scope staged_dev --options-file AIDE_OPTIONS.json --prior-intake PREVIOUS_INTAKE.json --prior-root ABSOLUTE_PREVIOUS_ROOT --review-ref ORIGINAL_REVIEW_REF --out-plan ABSOLUTE_NEW_PLAN.json
~~~

The task must have a distinct ID in the same project. The compiler compares
exact previously observed artifact bytes; it does not authenticate the
review reference, prior execution, scientific outcome or H3/H4/H6. No
unverified literature or prior score selects a scientific question or changes
an author decision automatically. Use PD-RW-Agent/ChatGPT for the original
independent assessment and task choice; no extra review is needed merely
because a different provider will be used.

The existing advise interface also accepts --intake-root ABSOLUTE_ROOT to
compare exact observed artifact bytes and retain that observation in its
handoff. It still requires original evidence review and does not turn byte
equality into a trusted Run. AIDE/RD scored replay intake includes the scored
prediction's digest bound to the observed artifact list. No candidate
execution or live cross-provider relay is implied by offline tests.

## Public dataset discovery (Zenodo via ToolUniverse)

The same ToolUniverse adapter now supports a narrow dataset lookup, directly
reusing the pinned ZenodoRESTTool and upstream config. Use the TaskPacket
capability dataset_lookup with public_topic scope, or pass this native plan:

~~~json
{"schema_version":"tooluniverse-public-dataset-v1","project_id":"PUBLIC-EXAMPLE","task_id":"DATA-001","attempt_id":"zenodo-001","operation":"dataset","public_text":"wearable inertial sensor human activity","limit":10}
~~~

The existing preview/query/collect commands are unchanged. Explicit public
network opt-in covers Zenodo only when the operator has approved that endpoint
and query; no dataset file is downloaded. The native query is restricted to
dataset metadata, results are screened for the declared dataset resource
type and deduplicated by record ID. The output datasets.json retains DOI,
title, version, publication date, access and license declarations, not the
files, labels or contents. A returned record, open-access declaration or
license ID is not proof of eligibility, data usability, or H4. Inspect
actual license terms, data schema, participants/groups, labels, ground truth,
condition coverage, closest prior work and achievable independent evaluation
before selecting data or requesting any download. Search totals are not
evidence of completeness. Unit tests use synthetic responses; no live
provider lookup or download was executed in this change.

## Custom RD-Agent DEV tasks

The custom DataScienceScen uses a local competition directory and a debug
sample directory. For a real task, the operator stages identical approved
flat DEV snapshots in both ROOT/worker/ds_data/pdrw-dev-task/ and
ROOT/worker/ds_data/sample/pdrw-dev-task/. Use the same exact
ROOT/review/manifest.json format as AIDE DEV, with identical project/task
IDs and manifest digest. No eval directory, answer file, arbitrary sampling
script or other competition is permitted. The two copies are checked,
not generated or copied by this tool. A sample_submission.csv, if required,
must contain format-only placeholders and be in the manifest. The actual
host must ensure no held-back labels are present under any name.
Use TaskPacket task_type=code_experiment, capability=research_iteration,
scope=staged_dev to prefer RD-Agent, with native options:

~~~json
{"attempt_id":"rd-001","goal":"Scoped candidate model","evaluation":"Original grouped DEV protocol and submission format","protocol_ref":"P/PROTOCOL","data_manifest_sha256":"<manifest digest>","loops":1,"steps":5,"timeout_seconds":600,"provider_config_sha256_declared":"<approved .env digest>"}
~~~

Compile with the existing specialists compile command. Stage creates two
identical description.md files; it never runs candidate code or starts the
provider. Verify checks manifest bytes, both data trees and descriptions.
The native environment settings are shared with the existing RD pilot;
inspect actual configuration, including Docker mounts, effective model
egress and eval_sub_dir, before launch. RD-Agent describes dataset contents
to its model, so ordinary DEV permission alone is not external transfer
permission. Native metric inference/score is not the original evaluator.

~~~powershell
pdrw-orch rdagent-dev stage --root ABSOLUTE_DEV_ROOT --plan-file RD_PLAN.json
pdrw-orch specialist-host prepare --provider rdagent --root ABSOLUTE_DEV_ROOT --plan-file RD_PLAN.json --source-root ABSOLUTE_SOURCE_PARENT
# Existing host runs only with verified permission and isolation.
pdrw-orch specialist-host collect --provider rdagent --root ABSOLUTE_DEV_ROOT --plan-file RD_PLAN.json
~~~

Export selected main.py, scores.csv, submission.csv and preserve the entire
candidate workspace for independent project-specific replay. The synthetic
scorer is not valid for custom DEV. Use original PD-RW evidence and evaluator
to judge candidate performance. No live execution is established by these
tests.

## Concentrated real-host acceptance

Use [SPECIALIST_HOST_ACCEPTANCE.md](SPECIALIST_HOST_ACCEPTANCE.md) as one
bounded WorkBuddy/Codex task. Existing advise now adds a provider-specific
scientific focus to the SAME independent review task: actual nearest papers
for discovery, independent truth and license for datasets, and evidence-to-
contribution judgment for algorithms. It does not generate another review
round, prove novelty or change the existing decision/authorization gate.

## Next development / evaluation

After the first actual AIDE result, compare a matched general host with
PD-RW-Agent vs AIDE under equivalent evidence, protocol and resource budget.
Measure real calls/tokens/time/cost, reproducibility and independently valid
scientific contribution. RD-Agent and ARC interfaces now also require live acceptance; prioritize a real AIDE result before adding further speculative providers.
The existing mock, Codex/Claude and source bridge stay compatible. Neither the
catalog nor preview/collect makes general registry agents ready. No live
specialist run or scientific benefit is claimed by CI.

Native source contract coverage is now a separate [workflow](../.github/workflows/specialist-native.yml), not a live service or autonomous search test. It is distinct from ordinary unit tests and from local operator acceptance.
