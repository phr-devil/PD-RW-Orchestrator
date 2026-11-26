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

## Next development / evaluation

After the first actual AIDE result, compare a matched general host with
PD-RW-Agent vs AIDE under equivalent evidence, protocol and resource budget.
Measure real calls/tokens/time/cost, reproducibility and independently valid
scientific contribution. RD-Agent and ARC interfaces now also require live acceptance; prioritize a real AIDE result before adding further speculative providers.
The existing mock, Codex/Claude and source bridge stay compatible. Neither the
catalog nor preview/collect makes general registry agents ready. No live
specialist run or scientific benefit is claimed by CI.
