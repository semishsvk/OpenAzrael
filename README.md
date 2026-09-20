# OpenAzrael

## Current status — v116-context-v31

**Technical base:** `openazrael_godot_poc_v116`  
**Runtime:** Godot 4  
**Active slice:** R1 -> R7 -> R8  
**Current candidate:** KG-001 Candidate 2  
**Candidate source status:** SOURCE_CONTRACT_PASS / independent-audit hardening wired / restored-asset runtime retest required  
**Observed Candidate 1 status:** manual FAIL — Issue #6 floor collision, Issue #9 no audible audio, Issue #11 magenta color-key textures  
**Candidate 2 v31 runtime status:** NOT_EXECUTED  
**Known-good tag:** `demo-known-good-001` — NOT ALLOWED until G00-G10 all pass

### Immediate priority
1. Restore the ignored Candidate room/audio/texture assets with `tools/restore_candidate_assets.py`; the restore derives `#` transparency from used indexed AZF palette keys and rebuilds GLB `MASK` materials.
2. Run `python tools/run_kg001_candidate_v112.py --fresh-checkout --visual-capture --promote-results`; the runner generates the per-build fingerprint manifest and now optionally includes canonical R1/R7/R8 graphical capture in the same evidence cycle.
3. Require all blocker regressions to PASS: canonical R1/R7/R8 floor support (#6), PCM + Master-bus physical audio readiness (#9), indexed color-key source/asset validation (#11), and the requested graphical capture contract.
4. Export/launch `Windows Candidate 2` and manually verify floor stability, actually audible audio, and no pink/magenta cutout background.
5. Continue the full R1 -> R7 -> R1 -> R8 -> Shield route only after those blocker retests pass; `demo-known-good-001` remains blocked while any release blocker is recorded.

### Current architectural decisions
- Evidence-first flow remains `original data -> forensic/import tools -> OpenAzrael IR -> Godot runtime`.
- Candidate diagnostics are observational only; they do not directly mutate gameplay state.
- Candidate evidence is run-scoped with run/build provenance; F11 packages the current run manifest, build manifest, state, telemetry tail and screenshot without commercial payload bytes.
- Candidate 2 source validation is pinned to Python 3.11.11 / NumPy 2.3.5 / Pillow 12.3.0 / trimesh 5.1.0 / Godot 4.7.2.stable.official.ed1daf0bf.
- Localization architecture is approved: stable semantic IDs, POT/PO authoring, built-in English fallback, external versioned PCK language packs, no core-resource replacement. Runtime implementation is deliberately deferred until after the first clean Candidate 2 runtime/manual validation.
- Existing forensic HOLDs remain HOLD; documentation cleanup does not promote any unresolved claim.

For canonical context start with `OPENAZRAEL_CONTEXT.md`, `docs/PROJECT_STATE.md`, `docs/LAST_SESSION.md`, and `data/project_context.json`.

---

