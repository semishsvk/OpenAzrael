# OpenAzrael Last Session

**Checkpoint prepared:** `v116-context-v32`  
**Date:** 2026-09-20  
**Technical base:** `openazrael_godot_poc_v116`

## Current canonical state
- Candidate 1 manual testing found **Critical Issue #6** (player falls through the floor), **Major Issue #9** (no audible audio), and **Major Issue #11** (legacy cutout textures show magenta instead of transparency).
- Candidate 2 / v32 is source-refrozen after an evidence-driven color-key correction, with all three blocker fixes: two-sided legacy floor collision plus R1/R7/R8 entry probes, physical audio readiness, and indexed-AZF binary color-key transparency.
- Actual ATDEMO audit covered all 86 AZFs: all 10 `#` textures have exactly one used raw R=255/B=255/G<=8 source sentinel and no non-`#` texture uses it. `BLOOS4#` contains one additional near-magenta non-key pixel, which forced the v31 rule correction.
- Independent local asset-pipeline replay generated 86 PNGs plus R1/R7/R8 GLBs with expected geometry counts; KEYHOLE#/MINETON# exported as MASK. This corroborates the asset fix but is not Godot runtime evidence.
- Issue #9 repair restores the source-safe legacy ambient IR dependency, fixes null `godot_position` fallback, tracks Event-IR physical players, requires all 7 Candidate event/ambient WAVs in graphical runs, and adds an audio-v116 runtime regression.
- Candidate 1 manual evidence remains FAIL. Candidate 2 is source-ready but NOT_EXECUTED; Issues #6/#9/#11 require restored-asset/runtime and manual retest.
- Added source-contract bug reporting: F11 creates a source-safe ZIP with screenshot, state snapshot/hash, telemetry tail and system metadata; GitHub issue intake and regression workflow are tracked in-repo.
- KG-001 Candidate 2 remains the active integration target.
- Candidate diagnostics source contract is PASS and the candidate is source-frozen pending runtime evidence.
- Canonical Godot runtime evidence is still **NOT_EXECUTED**.
- `demo-known-good-001` remains forbidden until G00-G10 are all literal PASS.
- Localization architecture is approved but runtime implementation is intentionally deferred until after the first clean Candidate 2 runtime/manual cycle.
- Existing forensic HOLDs remain unchanged.

## Documentation consistency update
- Refreshed README to lead with the source-frozen Candidate 2 / v32 stabilization status while preserving Candidate 1 failure evidence.
- Replaced stale roadmap items that still targeted already completed v113-v115 work.
- Aligned TEST_MATRIX, PROJECT_STATE, bootstrap context and artifact index on `v116-context-v32`.
- Preserved historical milestone notes rather than rewriting project history.
- Kept runtime/forensic boundaries explicit: documentation cleanup does not count as Godot execution and does not promote any evidence status.

## Current blockers / pending gates
- **Issue #6 — Critical:** player floor collision; source fix ready, Godot runtime/manual retest required.
- **Issue #9 — Major:** physical audio source fix ready; Godot runtime/manual audibility retest required.
- **Issue #11 — Major:** legacy `#` color-key alpha source fix ready; corrected asset rebuild and visual retest required.
- Real Godot execution of v109/v110/v111 remains pending in the canonical evidence set.
- R1/R7/R8 ignored room assets must be restored locally.
- Non-headless Candidate 2 requires the four Event-IR WAVs S152V2/S137/S121/799SECDR plus ambient S174ELP1/S174ELP2/S186 and source-safe legacy_world_ir metadata.
- G09 fresh-checkout build evidence and G10 final manual sanity remain pending.
- Complete PUZZLES/ROOMS -> WORLD producer/compiler remains HOLD.
- Original-runtime Classic audio pan/volume parity remains UNOBSERVED/HOLD.
- Deferred generic copy/mutator producer investigation is designated v117.

## Exact next action
1. Do not add Candidate features. Restore room/audio/texture assets with the v32 refrozen pipeline and run `python tools/run_kg001_candidate_v112.py --fresh-checkout --promote-results`.
2. Require v109, v110, v111, audio-v116 and texture color-key validation all to PASS; specifically require Issue #6/#9/#11 regressions.
3. Export/relaunch Candidate 2 and verify stable R1 floor support, actually audible R1 ambient audio, and correct transparent keyhole/tongs with no pink background.
4. Keep Issues #6/#9/#11 and G10 blocked until those manual retests pass.
5. Only then continue the complete demo route and remaining KG-001 acceptance.
