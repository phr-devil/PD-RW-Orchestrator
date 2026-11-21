# Policy & Guidance Contract

## Levels and authority

- **P0 EXTERNAL:** original PD-RW rules, original source records, authenticated author grants; never copied or overridden here.
- **P1 REQUIREMENT:** clearly sourced user operational preferences, optionally `deny_effects`; a config file is not an authenticated authorization or permission.
- **P2 MUST_CONSIDER:** require a relevance decision and short rationale, not mandatory retraining or a second checker.
- **P3 RECOMMENDATION:** opportunistic technical advice, freely rejected on grounded reasons.
- **P4 EXPERIENCE:** sourced conditional lessons from PD-RW-Experience. Advisory only regardless of its proposed strength.

The resolver validates schema, unique IDs, task applicability and contradictions. It never automatically elevates experience to P1 or scientific truth.

### Runtime packet

Each applicable rule includes ID, level, source, text, conditions, and optional evidence refs in `selected_items`. A compiler must not infer that listed evidence has been re-read or verified. The packet is small (default maximum 8), and all selected items explicitly label their *limited* authority.

A rule with `conditions` is a **conditional candidate** (`CONDITIONAL_UNVERIFIED`) until grounded applicability is checked by the responsible agent or trusted source. It must not be treated as already applying. P1 `deny_effects` are conservatively applied to matching task types while those conditions remain unresolved; neither the existence nor absence of such a rule can grant execution permission.

Unknown or conflict states are surfaced explicitly rather than silently pretending PASS. This module has **no** authority to interpret frozen protocols, authenticate user decisions, certify scientific validity or access reserved data.

### Scope

Use `task_types` with exact match or `*`. No evaluation of arbitrary Python expressions, regex from untrusted text, or dynamic shell commands. `deny_effects` on a requirement blocks affected *routing* even before host authorization. P0 host capability checks remain separate.

### Example

`policies/user/research-guidance.example.yaml` is a developer template only. Copy to a gitignored `*.local.yaml` and explicitly activate it; it must never be mistaken for a message granting permissions. Future Experience provider returns L4 lessons with source and applicability, not hard rules.

### Merge rules

Two rules with the same ID but different bodies are a validation error; no silent overwrite. Lower-priority advice that contradicts original frozen protocol cannot supersede it. User intent changes must be sourced to actual user messages through the host. Lessons require author review to propose modifying PD-RW itself.

### Token efficiency

Load only relevant policy IDs, the active PD-RW authority document, original evidence when needed; never all historical records for an ordinary DEV code modification. A meaningful Run or branch change may trigger review; each small loop must not.
