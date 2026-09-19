# OpenAzrael

## Current status — v116-context-v26

**Technical base:** `openazrael_godot_poc_v116`  
**Runtime:** Godot 4  
**Active slice:** R1 -> R7 -> R8  
**Current candidate:** KG-001 Candidate 1  
**Candidate source status:** SOURCE_CONTRACT_PASS / source-ready  
**Godot runtime status:** NOT_EXECUTED in the canonical evidence set  
**Known-good tag:** `demo-known-good-001` — NOT ALLOWED until G00-G10 all pass

### Immediate priority
1. Restore ignored R1/R7/R8 room assets and the four golden Event-IR WAVs on a Godot-capable checkout.
2. Run `python tools/run_kg001_candidate_v112.py --fresh-checkout --promote-results`.
3. If G00-G09 are literal PASS, launch KG-001 Candidate 1 interactively and complete the G10 manual sanity route using F6/F7/F10 diagnostics as needed.
4. Only after the first clean Candidate 1 runtime/manual cycle begin the approved localization runtime implementation and resume deferred v117 forensic work.

### Current architectural decisions
- Evidence-first flow remains `original data -> forensic/import tools -> OpenAzrael IR -> Godot runtime`.
- Candidate diagnostics are observational only; they do not directly mutate gameplay state.
- Localization architecture is approved: stable semantic IDs, POT/PO authoring, built-in English fallback, external versioned PCK language packs, no core-resource replacement. Runtime implementation is deliberately deferred until after Candidate 1 validation.
- Existing forensic HOLDs remain HOLD; documentation cleanup does not promote any unresolved claim.

For canonical context start with `OPENAZRAEL_CONTEXT.md`, `docs/PROJECT_STATE.md`, `docs/LAST_SESSION.md`, and `data/project_context.json`.

---

