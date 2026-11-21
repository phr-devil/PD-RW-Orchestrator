# M1 slice: real PD-RW-Agent read-only inspection

The adapter uses the **actual** PD-RW-Agent v1.0 RC CLI:
`python -m pdrw_agent.cli resume --project-id ID`.
It deliberately calls only one read-only `resume` instead of repeatedly calling `context`, `audit` and `rules`.

## Setup (on the operator's machine only)

Install the trusted PD-RW-Agent RC checkout in a Python environment (pin the checked-out commit; checked GitHub RC head: `9177b6eb822aaa0d1482ef40f54369a8612c42dd`). Keep the project mapping file private; the RC CLI requires `PDRW_AGENT_CONFIG` and `PDRW_WORKFLOW_ROOT`.

~~~powershell
$env:PDRW_AGENT_CONFIG = "D:\\private\\project-map.local.json"
$env:PDRW_WORKFLOW_ROOT = "D:\\local\\Problem-Data-Research-Workflow"
pdrw-orch pdrw inspect --project-id 19 --python "D:\\path\\to\\pdrw-agent-venv\\Scripts\\python.exe"
~~~

Adapt these **illustrative paths** to local reality; the CLI does not try to locate, change or register projects. An unregistered project returns a scoped upstream error rather than searching disks. Output is **redacted operational metadata**: source status, declared active task, unresolved operation count, and non-executable next-action hint.

- A successful CLI call is `SOURCE_REVIEW_ONLY`, never project identity authentication.
- The bridge never returns original snapshot text, paths, map contents or raw case data.
- `authorization_verified`, `execution_authorized`, `restart_permitted` and scientific completion are always false.
- If a task is blocked by identity, source inconsistency or uncertain prior process, preserve the status and review original records before acting.
- No effects, downloads, training, retries or new Run creation are enabled.
- The bridge assumes a trusted operator-selected local Python environment; running untrusted Python packages is *not* a sandbox. The host must still implement real resource/path/network controls.

No real user research project was accessed or accepted as part of this code slice. Integration tests simulate the upstream CLI JSON and error cases; actual WorkBuddy-MCP use remains unmeasured.
