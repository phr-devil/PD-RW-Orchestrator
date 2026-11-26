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
| microsoft/RD-Agent | Scenario-specific research/development iteration | README screened, no adapter |
| aiming-lab/AutoResearchClaw | Literature, hypothesis, staged pipeline | README screened, no adapter |

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

## Next development / evaluation

After the first actual AIDE result, compare a matched general host with
PD-RW-Agent vs AIDE under equivalent evidence, protocol and resource budget.
Measure real calls/tokens/time/cost, reproducibility and independently valid
scientific contribution. Choose RD-Agent or ARC next only for complementary
capability; ARC must support a bounded stage and no automatic manuscript.
The existing mock, Codex/Claude and source bridge stay compatible. Neither the
catalog nor preview/collect makes general registry agents ready. No live
specialist run or scientific benefit is claimed by CI.
