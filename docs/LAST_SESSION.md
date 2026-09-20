# OpenAzrael Last Session

**Checkpoint prepared:** `v116-context-v31`  
**Date:** 2026-09-20  
**Technical base:** `openazrael_godot_poc_v116`

## Current canonical state
- Candidate 1 manual testing found **Critical Issue #6** (player falls through the floor), **Major Issue #9** (no audible audio), and **Major Issue #11** (legacy cutout textures show magenta instead of transparency).
- Candidate 2 / v31 carries the independent-audit hardening for all three blocker fixes: two-sided collision plus canonical R1/R7/R8 floor probes; PCM and Master-bus audio non-silence checks; indexed-AZF exactly-one-key transparency with fail-closed ambiguity handling and MASK hidden-RGB edge bleed.
- Candidate evidence is now run-scoped with `run_id`, build commit identity, `run_manifest.json`, `events.jsonl`, state dumps and F11 provenance packages.
- The Candidate toolchain/export path is source-safe and pinned: Python 3.11.11 / NumPy 2.3.5 / Pillow 12.3.0 / trimesh 5.1.0 / Godot 4.7.2. v118 adds a complete-asset pre-build gate, build-manifest schema v2 runtime/export identity fingerprints, exported-EXE startup smoke and a `READY_FOR_G10_MANUAL_TEST` receipt.
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
- The complete local Candidate 2 asset set must be restored: R1/R7/R8 rooms, exactly 86 Classic textures and all 8 runtime WAVs (797TAP plus the seven Event/ambient WAVs).
- G09 fresh-checkout build evidence and G10 final manual sanity remain pending.
- Complete PUZZLES/ROOMS -> WORLD producer/compiler remains HOLD.
- Original-runtime Classic audio pan/volume parity remains UNOBSERVED/HOLD.
- Deferred generic copy/mutator producer investigation is designated v117.

## Exact next action
1. On Windows run `pwsh tools/run_kg001_candidate2_windows_v117.ps1 -DemoDir <ATDEMO> -Godot <Godot_4.7.2.exe> -PromoteResults`.
2. Require the v118 complete-asset gate, v109/v110/v111/audio-v116, indexed texture validation, G09 fresh-checkout and requested R1/R7/R8 graphical capture all to PASS.
3. Require `Windows Candidate 2` export plus exported-EXE startup smoke PASS and the sidecar receipt status `READY_FOR_G10_MANUAL_TEST`.
4. Perform G10 manually: floor stability, actually audible audio, correct transparency/no fringe, complete intended demo route and zero reproducible softlocks.
5. Keep Issues #6/#9/#11 and `demo-known-good-001` blocked until those manual checks pass; only then resume main gameplay development.
