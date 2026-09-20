# OpenAzrael

## Candidate 2 Windows execution — 2026-09-20

**KG-001 Candidate 2 / v116-context-v32: G00-G09 PASS; G10 PENDING_MANUAL_USER.**
Tested source `89ccf775dfd6abc21e6bc69f344fe2d349b4dd70`, Godot `4.7.2.stable.official.ed1daf0bf`.
The clean-checkout suite passed source validation, asset import, v109, v110,
v111 and audio-v116 (62 checks). The exported Windows EXE passed headless and
graphical smoke tests. Instrumented exported-PCK checks passed real floor
support in R1/R7/R8, nonzero Master audio output, cutout materials and F11 ZIP
capture without a gameplay-state hash change. Supplied Sigil icons are verified
inside the executable. Some headless scene tests report non-fatal ObjectDB
cleanup warnings; there are no ERROR or SCRIPT ERROR lines in the passing runs.

Additional integration fixes preserve the authored invisible R8/Object01
entrance support collision, repair empty ambient WAV loop ranges, and retain
Godot numeric typing and runner error handling. The v32 indexed palette rule
preserves the single near-magenta non-key pixel in BLOOS4#.

Candidate 1 manual failure remains historical evidence. Issues #6, #9 and #11
await human retest and remain release blockers. No `demo-known-good-001` tag
is allowed or created. Original Miles parity and complete original renderer
transparency semantics remain HOLD. See `docs/CANDIDATE2_WINDOWS.md` and
`data/tests/kg001_candidate2_windows.json` for details.

## Current status — v116-context-v32

**Technical base:** `openazrael_godot_poc_v116`  
**Runtime:** Godot 4  
**Active slice:** R1 -> R7 -> R8  
**Current candidate:** KG-001 Candidate 2  
**Candidate source status:** SOURCE_REFROZEN_V32 / Windows exported / manual retest required  
**Observed Candidate 1 status:** manual FAIL — Issue #6 floor collision, Issue #9 no audible audio, Issue #11 magenta color-key textures  
**Candidate 2 v32 runtime status:** AUTOMATED_PASS_MANUAL_PENDING  
**Known-good tag:** `demo-known-good-001` — NOT ALLOWED until G00-G10 all pass

### Immediate priority
1. Restore the ignored Candidate room/audio/texture assets with `tools/restore_candidate_assets.py`; the restore now rebuilds legacy indexed `#` color-key masks as binary alpha.
2. Run `python tools/run_kg001_candidate_v112.py --fresh-checkout --promote-results`.
3. Require all three blocker regressions to PASS: v110 R1/R7/R8 floor support (#6), audio-v116 physical readiness (#9), and audited source-palette color-key source/asset validation (#11).
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

