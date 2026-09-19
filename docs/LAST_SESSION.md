# OpenAzrael Last Session

**Checkpoint prepared:** `v116-context-v29`  
**Date:** 2026-09-19  
**Technical base:** `openazrael_godot_poc_v116`

## Current canonical state
- Candidate 1 manual testing found **Critical Issue #6**: the player falls through the floor, and **Major Issue #9**: no audible audio.
- Candidate 2 / v29 keeps the two-sided legacy floor-collision fix and adds a physical audio-readiness gate.
- Issue #9 repair restores the source-safe legacy ambient IR dependency, fixes null `godot_position` fallback, tracks Event-IR physical players, requires all 7 Candidate event/ambient WAVs in graphical runs, and adds an audio-v116 runtime regression.
- Candidate 1 manual evidence remains FAIL. Candidate 2 is source-ready but NOT_EXECUTED; both blockers require automated and manual retest.
- Added source-contract bug reporting: F11 creates a source-safe ZIP with screenshot, state snapshot/hash, telemetry tail and system metadata; GitHub issue intake and regression workflow are tracked in-repo.
- KG-001 Candidate 2 remains the active integration target.
- Candidate diagnostics source contract is PASS and the candidate is source-ready.
- Canonical Godot runtime evidence is still **NOT_EXECUTED**.
- `demo-known-good-001` remains forbidden until G00-G10 are all literal PASS.
- Localization architecture is approved but runtime implementation is intentionally deferred until after the first clean Candidate 1 runtime/manual cycle.
- Existing forensic HOLDs remain unchanged.

## Documentation consistency update
- Refreshed README to lead with the actual v116 Candidate 1 status instead of old historical checkpoints.
- Replaced stale roadmap items that still targeted already completed v113-v115 work.
- Aligned TEST_MATRIX, PROJECT_STATE, bootstrap context and artifact index on `v116-context-v29`.
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
1. Restore Candidate room/audio assets and run `python tools/run_kg001_candidate_v112.py --fresh-checkout --promote-results` on Candidate 2 / v29.
2. Require v109, v110, v111 and audio-v116 all to PASS; specifically require the Issue #6 floor regression and Issue #9 physical-audio regression.
3. Export/relaunch Candidate 2 and first verify stable R1 floor support plus actually audible R1 ambient audio.
4. Keep Issues #6/#9 and G10 blocked until those manual retests pass.
5. Only then continue the complete demo route and remaining KG-001 acceptance.
