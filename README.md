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
2. Prefer the Windows v118 handoff wrapper. Fresh-checkout now requires the complete restored set: 3 room GLBs, all 8 runtime WAVs including `797TAP.WAV`, exactly 86 Classic PNGs and all 10 valid indexed-key `#` textures.
3. Require all blocker regressions plus canonical R1/R7/R8 graphical capture to PASS; the build manifest must match current HEAD and fingerprint the runtime/export source identity.
4. Export `Windows Candidate 2`, require the exported EXE headless startup smoke to PASS with no critical script/resource-load errors, and obtain a `READY_FOR_G10_MANUAL_TEST` receipt before manual testing.
5. Continue the full R1 -> R7 -> R1 -> R8 -> Shield route only after those blocker retests pass; `demo-known-good-001` remains blocked while any release blocker is recorded.

### Windows local handoff
For the full restored-asset cycle on Windows, use the thin canonical wrapper:

    pwsh tools/run_kg001_candidate2_windows_v117.ps1 -DemoDir C:\path\to\ATDEMO -Godot C:\path\to\Godot_v4.7.2-stable_win64.exe -PromoteResults

It delegates to the canonical restore/runner/export contracts, exports from the clean validated checkout, smoke-launches the real EXE, records package hashes and emits a v118 test-build receipt. Evidence promotion occurs only afterwards. It does not implement separate gameplay or acceptance logic.

### Current architectural decisions
- Evidence-first flow remains `original data -> forensic/import tools -> OpenAzrael IR -> Godot runtime`.
- Candidate diagnostics are observational only; they do not directly mutate gameplay state.
- Candidate evidence is run-scoped with run/build provenance; F11 packages the current run manifest, build manifest, state, telemetry tail and screenshot without commercial payload bytes.
- Candidate 2 source validation is pinned to Python 3.11.11 / NumPy 2.3.5 / Pillow 12.3.0 / trimesh 5.1.0 / Godot 4.7.2.stable.official.ed1daf0bf.
- Localization architecture is approved: stable semantic IDs, POT/PO authoring, built-in English fallback, external versioned PCK language packs, no core-resource replacement. Runtime implementation is deliberately deferred until after the first clean Candidate 2 runtime/manual validation.
- Existing forensic HOLDs remain HOLD; documentation cleanup does not promote any unresolved claim.

For canonical context start with `OPENAZRAEL_CONTEXT.md`, `docs/PROJECT_STATE.md`, `docs/LAST_SESSION.md`, and `data/project_context.json`.

---

