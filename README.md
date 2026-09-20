# OpenAzrael

## Current status — v116-context-v31

**Technical base:** `openazrael_godot_poc_v116`  
**Runtime:** Godot 4  
**Active slice:** R1 -> R7 -> R8  
**Current candidate:** KG-001 Candidate 2  
**Candidate source status:** SOURCE_CONTRACT_PASS / blocker fixes wired / runtime retest required  
**Observed Candidate 1 status:** manual FAIL — Issue #6 floor collision, Issue #9 no audible audio, Issue #11 magenta color-key textures  
**Candidate 2 v30 runtime status:** NOT_EXECUTED  
**Known-good tag:** `demo-known-good-001` — NOT ALLOWED until G00-G10 all pass

### Immediate priority
1. Restore the ignored Candidate room/audio/texture assets with `tools/restore_candidate_assets.py`; the restore now rebuilds legacy `#` color-key masks as binary alpha.
2. Run `python tools/run_kg001_candidate_v112.py --fresh-checkout --promote-results`.
3. Require all three blocker regressions to PASS: v110 floor support (#6), audio-v116 physical readiness (#9), and texture color-key source/asset validation (#11).
4. Export/launch Candidate 2 and manually verify stable R1 floor collision, audible R1 ambient audio, and no pink/magenta background on the keyhole/tongs or other `#` cutout textures.
5. Continue the full R1 -> R7 -> R1 -> R8 -> Shield route only after those blocker retests pass; `demo-known-good-001` remains blocked while any release blocker is recorded.

### Current architectural decisions
- Evidence-first flow remains `original data -> forensic/import tools -> OpenAzrael IR -> Godot runtime`.
- Candidate diagnostics are observational only; they do not directly mutate gameplay state.
- F11 captures a source-safe diagnostic ZIP for GitHub Issues; see `docs/BUG_REPORTING.md`.
- Localization architecture is approved: stable semantic IDs, POT/PO authoring, built-in English fallback, external versioned PCK language packs, no core-resource replacement. Runtime implementation is deliberately deferred until after the first clean Candidate 2 runtime/manual validation.
- Existing forensic HOLDs remain HOLD; documentation cleanup does not promote any unresolved claim.

For canonical context start with `OPENAZRAEL_CONTEXT.md`, `docs/PROJECT_STATE.md`, `docs/LAST_SESSION.md`, and `data/project_context.json`.

---

