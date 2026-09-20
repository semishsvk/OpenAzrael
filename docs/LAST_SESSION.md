# OpenAzrael Last Session

**Checkpoint prepared:** `v116-context-v31`  
**Date:** 2026-09-20  
**Technical base:** `openazrael_godot_poc_v116`

## Current canonical state
- Candidate 1 manual testing found **Critical Issue #6** (player falls through the floor), **Major Issue #9** (no audible audio), and **Major Issue #11** (legacy cutout textures show magenta instead of transparency).
- Candidate 2 / v31 carries the independent-audit hardening for all three blocker fixes: two-sided collision plus canonical R1/R7/R8 floor probes; PCM and Master-bus audio non-silence checks; indexed-AZF exactly-one-key transparency with fail-closed ambiguity handling and MASK hidden-RGB edge bleed.
- Candidate evidence is now run-scoped with `run_id`, build commit identity, `run_manifest.json`, `events.jsonl`, state dumps and F11 provenance packages.
- The Candidate toolchain/export path is source-safe and pinned: Python 3.11.11 / NumPy 2.3.5 / Pillow 12.3.0 / trimesh 5.1.0 / Godot 4.7.2; a generated build manifest fingerprints local assets without embedding them.
- Canonical R1/R7/R8 visual capture is formalized as observational 1280x720 evidence, not a cross-GPU pixel-perfect hash oracle.
- Candidate 1 manual evidence remains FAIL. Candidate 2 is source-ready but NOT_EXECUTED; Issues #6/#9/#11 require restored-asset/runtime and manual retest.
- Added source-contract bug reporting: F11 creates a source-safe ZIP with screenshot, state snapshot/hash, telemetry tail and system metadata; GitHub issue intake and regression workflow are tracked in-repo.
- KG-001 Candidate 2 remains the active integration target.
- Candidate diagnostics source contract is PASS and the candidate is source-ready.
- Canonical Godot runtime evidence is still **NOT_EXECUTED**.
- `demo-known-good-001` remains forbidden until G00-G10 are all literal PASS.
- Localization architecture is approved but runtime implementation is intentionally deferred until after the first clean Candidate 2 runtime/manual cycle.
- Existing forensic HOLDs remain unchanged.

## Documentation consistency update
- Refreshed README and bootstrap context to describe the v31 independent-audit hardening while preserving Candidate 1 failure evidence.
- Restored compact source-safe v103/v105/v106 forensic summaries required by clean-checkout context validation; no raw commercial-derived bytes were added.
- Aligned TEST_MATRIX, PROJECT_STATE, bootstrap context and artifact index on `v116-context-v31`.
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
1. Restore Candidate room/audio/texture assets with the v31 pipeline, generate the build fingerprint manifest, and run `python tools/run_kg001_candidate_v112.py --fresh-checkout --promote-results`.
2. Require v109, the R1/R7/R8 v110 floor matrix, v111, audio-v116 PCM/Master capture and indexed texture color-key validation all to PASS.
3. Run canonical R1/R7/R8 graphical captures, export/relaunch `Windows Candidate 2`, and verify stable floors, actually audible audio, and correct transparent cutouts with no pink background.
4. Keep Issues #6/#9/#11 and G10 blocked until those restored-asset/manual retests pass.
5. Only then continue the complete demo route and remaining KG-001 acceptance.
