# User guide (v0.1)

~~~bash
python -m pip install -e ".[dev]"
pdrw-orch doctor
pdrw-orch agents list
pdrw-orch policy check
pdrw-orch policy explain ALG-BASELINE --task-type experiment_design
pdrw-orch demo
python -m pytest -q
~~~

The demo runs in-memory using two mock agents; no real research, LLM, GPU, data download or scientific verification. Outputs use `DEMO_ONLY`.

Configuration files under `configs/*.example.yaml` and `policies/user/*.example.yaml` are examples. Local copies with `*.local.yaml` are gitignored. Do not put secrets, unpublished data or original project state in the repository.

Future commands (`start --project`, `resume`, `status`, `cancel`) require production host auth, process supervision and durable checkpoints and are not shipped in v0.1. No fake success promise.
