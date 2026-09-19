# OpenAzrael Last Session

**Checkpoint prepared:** `v116-context-v27`  
**Date:** 2026-09-19  
**Technical base:** `openazrael_godot_poc_v116`

## Current canonical state
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
- Aligned TEST_MATRIX, PROJECT_STATE, bootstrap context and artifact index on `v116-context-v27`.
- Preserved historical milestone notes rather than rewriting project history.
- Kept runtime/forensic boundaries explicit: documentation cleanup does not count as Godot execution and does not promote any evidence status.

## Current blockers / pending gates
- Real Godot execution of v109/v110/v111 remains pending in the canonical evidence set.
- R1/R7/R8 ignored room assets must be restored locally.
- Non-headless Candidate 1 requires S152V2.WAV, S137.WAV, S121.WAV and 799SECDR.WAV.
- G09 fresh-checkout build evidence and G10 final manual sanity remain pending.
- Complete PUZZLES/ROOMS -> WORLD producer/compiler remains HOLD.
- Original-runtime Classic audio pan/volume parity remains UNOBSERVED/HOLD.
- Deferred generic copy/mutator producer investigation is designated v117.

## Exact next action
1. Restore the ignored R1/R7/R8 room assets and required Candidate 1 audio assets.
2. Run `python tools/run_kg001_candidate_v112.py --fresh-checkout --promote-results`.
3. Evaluate the resulting G00-G09 evidence.
4. If G00-G09 are PASS, run the normal graphical Candidate 1 and traverse the full demo.
5. Complete G10 only after a clean manual run.
6. Only then consider the `demo-known-good-001` tag.
