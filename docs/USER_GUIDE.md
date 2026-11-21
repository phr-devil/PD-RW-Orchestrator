# User guide (M1-A)

~~~bash
python -m pip install -e ".[dev]"
pdrw-orch doctor
pdrw-orch agents list
pdrw-orch policy check
pdrw-orch policy explain ALG-BASELINE --task-type experiment_design
pdrw-orch demo
python -m pytest -q
~~~

These commands are mock-only and do not access original research data.

### Bounded read-only PD-RW-Agent inspection

If the actual operator-machine RC package and private project map are available, see [PDRW_BRIDGE.md](PDRW_BRIDGE.md). Then run:

~~~powershell
pdrw-orch pdrw inspect --project-id 19 --python "C:\\path\\to\\python.exe"
~~~

This only reads the project's *reported* compact operational state (through the installed RC CLI). No real external research agent is invoked; it does not grant permission or verify a scientific claim.

Configuration files under `configs/*.example.yaml` and `policies/user/*.example.yaml` are examples. Local copies with `*.local.yaml` are gitignored. Do not put secrets, unpublished data or original project state in the repository.

Production `start --project`, `resume`, `status`, `cancel` require a production host permission bridge, actual process supervision and durable checkpoints. They are not shipped in this phase.
