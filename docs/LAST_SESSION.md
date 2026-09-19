# OpenAzrael Last Session

## Windows integration attempt — 2026-09-19

Latest execution supersedes the earlier NOT_EXECUTED preparation notes below:
Godot 4.7.2 v109 PASS (13 checks); v110/v111 BLOCKED_MISSING_ASSETS.
Canonical demo GLBs and legacy ambient IR are still required. The available
retail prototype GLBs are not equivalent. Source-safe compile/runner fixes,
a Windows export preset and matching templates are prepared.
See `docs/CANDIDATE1_WINDOWS_ATTEMPT.md` for the exact boundary and resume steps.
G10 remains PENDING_MANUAL_USER; no known-good tag was created.


**Checkpoint prepared:** `v116-context-v24`
**Date:** 2026-09-18

## What changed
- Advanced technical base to **v116** and canonical context to **v116-context-v24**.
- v116 is now the diagnostic integration layer for **KG-001 Candidate 1**. The previously discussed but uncommitted producer/copy scan is deferred to v117.
- Added `CandidateDiagnostics` autoload with structured event telemetry and canonical DemoState SHA-256 on every recorded event.
- Added persistent non-headless event log: `user://openazrael_candidate1_events.jsonl`.
- Added F10 canonical state dumps under `user://openazrael_kg001_state_dump_<timestamp>_<sequence>.json`.
- Added F6 authored trigger-volume visualization and F7 Candidate diagnostics HUD.
- Preserved existing F8 audio debug and F9 audio parity capture unchanged in purpose.
- Logged interactions, trigger enter/exit edges, room transitions/loads, debug room jumps, inventory/flag/puzzle changes and logical audio.
- Changed R1/R7/R8 from script-time GLB preloads to runtime loads behind a deterministic fail-fast resource preflight.
- Non-headless Candidate 1 additionally requires the four golden Event-IR WAVs: S152V2, S137, S121 and 799SECDR.
- Added `tools/validate_candidate_diagnostics_v116.py` to the existing v112 candidate source suite and committed the v116 source contract.
- Hardened evidence parsing and suppressed noisy initial false trigger-edge events.
- Current v116 diagnostic source contract: **PASS**. Godot runtime execution remains **NOT EXECUTED** here.
- KG-001 final tag remains forbidden until G00-G10 all pass.

## Current blockers / HOLD
- v109/v110/v111 still need real Godot execution with locally restored ignored room assets.
- Candidate 1 non-headless run also requires the four golden Event-IR audio assets.
- G09 fresh-checkout and G10 final manual sanity remain pending.
- Complete PUZZLES/ROOMS -> WORLD producer/compiler remains HOLD.
- The deferred generic copy/mutator producer audit is now the v117 forensic target.
- Original-runtime Classic audio pan/volume parity remains UNOBSERVED/HOLD.

## Exact next action
On the development machine:
1. restore the ignored R1/R7/R8 room assets and required Candidate 1 audio assets;
2. run `python tools/run_kg001_candidate_v112.py --fresh-checkout --promote-results`;
3. if G00-G09 are PASS, launch the normal Godot Candidate 1 build and manually traverse the full demo using F6/F7/F10 diagnostics as needed;
4. complete G10 only after that manual run is clean.
