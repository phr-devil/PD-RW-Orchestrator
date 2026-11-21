# Agent instructions (short router only)

This repository builds an **operational orchestrator**, not a new research workflow.

1. Read README and one relevant docs file. PD-RW [WORKFLOW.md/AGENTS.md] owns scientific policy; original project records own scientific evidence. Do not re-implement them here.
2. Check code and tests before changing interfaces. Keep backward-compatible schemas and tests where feasible.
3. Policies: user requirement != authenticated permission; experience != scientific fact. Never promote external advice to a hard rule automatically.
4. Routine code changes: implement adjacent modules together, run focused tests once, report only results and real blockers. Avoid whole-repo rereading, repeated agents and verbose logs.
5. No protected project operations, data uploads, model paid runs, training, SEALED, manuscripts, or submissions without the original host grant and security controls.
6. Distinguish DEMO_ONLY, NOT_CONNECTED, ENGINEERING_SUCCESS, valid science and publication readiness.

Do not silently edit PD-RW, PD-RW-Agent, PD-RW-Experience or original research projects while working in this repository.
