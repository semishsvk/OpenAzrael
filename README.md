# OpenAzrael

## Current status — v116-context-v28

**Technical base:** `openazrael_godot_poc_v116`  
**Runtime:** Godot 4  
**Active slice:** R1 -> R7 -> R8  
**Current candidate:** KG-001 Candidate 1  
**Candidate source status:** SOURCE_FIX_READY / runtime retest required  
**Observed runtime status:** v27 manual FAIL — Critical Issue #6 (player falls through floor)  
**v28 runtime status:** NOT_EXECUTED  
**Known-good tag:** `demo-known-good-001` — NOT ALLOWED until G00-G10 all pass

### Immediate priority
1. Retest Critical Issue #6 on the v28 source: legacy room trimeshes now use two-sided concave collision.
2. Run `python tools/run_kg001_candidate_v112.py --fresh-checkout --promote-results`; v110 now includes a physical R1 floor-support regression using the real player capsule.
3. Launch the graphical Candidate and verify that the player no longer falls through the floor. Keep Issue #6 open until this manual retest passes.
4. Only after Issue #6 is cleared continue the full G10 sanity route; `demo-known-good-001` remains blocked.

### Current architectural decisions
- Evidence-first flow remains `original data -> forensic/import tools -> OpenAzrael IR -> Godot runtime`.
- Candidate diagnostics are observational only; they do not directly mutate gameplay state.
- F11 captures a source-safe diagnostic ZIP for GitHub Issues; see `docs/BUG_REPORTING.md`.
- Localization architecture is approved: stable semantic IDs, POT/PO authoring, built-in English fallback, external versioned PCK language packs, no core-resource replacement. Runtime implementation is deliberately deferred until after Candidate 1 validation.
- Existing forensic HOLDs remain HOLD; documentation cleanup does not promote any unresolved claim.

For canonical context start with `OPENAZRAEL_CONTEXT.md`, `docs/PROJECT_STATE.md`, `docs/LAST_SESSION.md`, and `data/project_context.json`.

---

