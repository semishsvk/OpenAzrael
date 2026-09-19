# OpenAzrael Last Session

**Checkpoint prepared:** `v116-context-v28`  
**Date:** 2026-09-19  
**Technical base:** `openazrael_godot_poc_v116`

## Current canonical state
- First graphical Candidate test found **Critical Issue #6**: the player falls through the floor.
- v28 source fix enables two-sided `ConcavePolygonShape3D` room collision and adds an asset-backed physical R1 floor-support regression to v110.
- The v27 manual observation is FAIL; the corrected v28 build is NOT_EXECUTED and must be retested before Issue #6 can close.
- Added source-contract bug reporting: F11 creates a source-safe ZIP with screenshot, state snapshot/hash, telemetry tail and system metadata; GitHub issue intake and regression workflow are tracked in-repo.
- KG-001 Candidate 1 remains the active integration target.
- Candidate diagnostics source contract is PASS and the candidate is source-ready.
- Canonical Godot runtime evidence is still **NOT_EXECUTED**.
- `demo-known-good-001` remains forbidden until G00-G10 are all literal PASS.
- Localization architecture is approved but runtime implementation is intentionally deferred until after the first clean Candidate 1 runtime/manual cycle.
- Existing forensic HOLDs remain unchanged.

## Documentation consistency update
- Refreshed README to lead with the actual v116 Candidate 1 status instead of old historical checkpoints.
- Replaced stale roadmap items that still targeted already completed v113-v115 work.
- Aligned TEST_MATRIX, PROJECT_STATE, bootstrap context and artifact index on `v116-context-v28`.
- Preserved historical milestone notes rather than rewriting project history.
- Kept runtime/forensic boundaries explicit: documentation cleanup does not count as Godot execution and does not promote any evidence status.

## Current blockers / pending gates
- **Issue #6 — Critical:** player floor collision; source fix ready, Godot runtime/manual retest required.
- Real Godot execution of v109/v110/v111 remains pending in the canonical evidence set.
- R1/R7/R8 ignored room assets must be restored locally.
- Non-headless Candidate 1 requires S152V2.WAV, S137.WAV, S121.WAV and 799SECDR.WAV.
- G09 fresh-checkout build evidence and G10 final manual sanity remain pending.
- Complete PUZZLES/ROOMS -> WORLD producer/compiler remains HOLD.
- Original-runtime Classic audio pan/volume parity remains UNOBSERVED/HOLD.
- Deferred generic copy/mutator producer investigation is designated v117.

## Exact next action
1. Run `python tools/run_kg001_candidate_v112.py --fresh-checkout --promote-results` on v28 with restored assets.
2. Require the new v110 Issue #6 floor regression to PASS.
3. Relaunch the graphical demo and verify the player remains on the R1 floor.
4. Keep Issue #6 open and G10 blocked until that retest passes.
5. Then continue the full manual route and the remaining KG-001 gates.
