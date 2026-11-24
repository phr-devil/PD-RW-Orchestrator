# M1-C — operator host acceptance tooling

## Status and authority

The original PD-RW-Agent RC `9177b6eb822aaa0d1482ef40f54369a8612c42dd`
exposes source-reported project/operation/Run status, but its operational
receipt contains no trustworthy PID/start-time binding. Its authorization
state is UNVERIFIED. Orchestrator never reconstructs an author grant from
those records and never creates a parallel authorization ledger.
This version implements local observation, not real project execution.

## One bounded operator acceptance pass

~~~powershell
git pull
python -m pip install -e ".[host]"
$env:PDRW_AGENT_CONFIG = "D:\private\project-map.json"
$env:PDRW_WORKFLOW_ROOT = "D:\PD-RW"
pdrw-orch host audit --project-id 19 --python "D:\PD-RW-Agent\.venv\Scripts\python.exe"
~~~

Use actual registered paths and IDs. Optional arguments:
`--operation-id OP-001 --run-id RUN-001 --task-id TASK-001` inspect explicit
original DEV/VAL references and compare declared Task identities. Do not
supply protected data IDs. The upstream CLI is executed with isolated
Python mode and bytecode writing disabled; it must be installed in the
selected interpreter, not discoverable only through PYTHONPATH.
The check samples metadata version, source version, and actual CLI file
SHA-256 before and after the source inspection. Version mismatch or drift
blocks the combined source result. Default expected RC is 1.0.0rc1.
An optional `--expected-cli-sha256` can compare against an independently
known trusted file's exact bytes; Windows CRLF changes the digest.
This does not authenticate every module, git revision, Skill, MCP or host.

## Local process identity

Only inspect an operator-selected PID. Do not discover unrelated processes.

~~~powershell
pdrw-orch host process --pid 12345
# Later, use the original baseline from the SAME machine, not a newly
# sampled identity for an unknown historical process:
pdrw-orch host process --pid 12345 --expected-created-at ORIGINAL_TIMESTAMP --expected-exe-path-sha256 ORIGINAL_HASH
~~~

- PROCESS_OBSERVED_UNBOUND: OS observed a live process, no existing baseline.
- PROCESS_MATCH_ALIVE: PID, creation time and normalized executable **path**
  fingerprint agree with the supplied earlier baseline at sampling time.
- PROCESS_IDENTITY_MISMATCH: baseline disagrees; possible PID reuse or changed executable.
- PROCESS_ABSENT_AT_SAMPLE / PROCESS_NOT_LIVE_AT_SAMPLE: PID not present or
  not live at sampling time; no conclusion about descendant processes.
- PROCESS_STATE_UNKNOWN / PROCESS_CHANGED_DURING_SAMPLE: observation unavailable
  or unstable. No retry or cancellation permitted.

The executable-path fingerprint is not a file-content hash. The operator's
baseline must be independently recorded at launch; a newly observed PID
does not prove association with an older operation. No process-list scan,
argv, username, raw executable paths, termination or restart is performed.

## Authorization and next acceptance gate

HOST_READ_ONLY_CHECKS_COMPLETE means only that requested read-only checks
completed; not permission to run or resume. All results explicitly keep
author_scope_verified, execution_authorized, operation_process_binding_verified,
restart_permitted and cancel_permitted false. The unknown original H6 scope
is not a demand for a new H6 decision: verify the existing original scope
through a future trusted source authorizer. Independent permitted read-only
work is not automatically prohibited by an old unknown job.

Remaining work: operator-machine acceptance with actual RC, Skill and MCP
alignment; host-owned operation/process binding at dispatch; authenticated
original grant adapter; isolated provider execution and real Agent handoff.
CI uses mock source calls and a real synthetic local child process. It does
not validate the user's actual project, invoke paid models or alter science.
