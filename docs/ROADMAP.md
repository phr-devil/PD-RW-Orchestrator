# Acceptance-driven roadmap

- **M0 (complete):** runnable minimal Python CLI, versioned contracts, deterministic policy filtering, mocked two-agent DAG and tests; no API calls.
- **M1-A (complete in CI):** bounded read-only PD-RW-Agent RC CLI `resume` bridge, privacy-preserving source status; conditional guidance content with provenance. Tests use simulated upstream responses.
- **M1-B (code / CI acceptance):** immutable local task plan, private SQLite *scheduling intents only*, restart-safe unresolved attempts and no automatic retry. Project roots and PD-RW science/operation receipts are not replicated. **Real operator-machine PD-RW-Agent integration is still pending**; this is not real research execution.
- **M1-C (next):** trusted operator-host binding to original project identity, PD-RW-Agent operation receipt correlation and checked process-liveness reconciliation; no blind process restart.
- **M2:** one real provider task, then second provider handoff. Validate actual CLI/API health, true output references, host permissions, local budget and cancellation. Mark external capability READY only after acceptance.
- **M3:** PD-RW-Experience provider: imported experience always advisory, source and time binding, contradiction and negative-transfer tests.
- **M4:** paired evaluation: single vs multi-Agent, with vs without experience, fixed models and total budget, held-out time-valid cases. Measure science error, evidence value, time, cost and interventions. Publication/citation outcomes remain observational.

Do not add an autonomous paper writer, second PD-RW policy file, second science ledger, heavy microservices, a web dashboard or whole-framework vendoring before M2 has evidence of real value.
