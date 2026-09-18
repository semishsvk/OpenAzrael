# OpenAzrael Last Session

**Checkpoint prepared:** `v112-context-v20`
**Date:** 2026-09-18

## What changed
- Advanced technical base to **v112** and canonical context to **v112-context-v20**.
- v108 exhaustive logical state-space remains source-model PASS with 63 states and 0 modeled softlocks.
- v109/v110/v111 runtime runners remain prepared but NOT EXECUTED in this environment.
- Added `tools/run_kg001_candidate_v112.py`: one command for source validators, Godot discovery, v109/v110/v111 runtime capture, Git cleanliness checks, repository-safety checks, ignored-room-asset checks and optional evidence promotion.
- Candidate evidence is written under ignored `.tmp/kg001/`; G09 clean_before and clean_after are captured before optional promotion dirties the checkout.
- Added `tools/kg001_status_v112.py`, which can promote G00-G09 to literal PASS only from recorded PASS evidence.
- Added the G10 human sanity checklist and a result template. G10 cannot be auto-promoted.
- Current overall status is **AWAITING_RUNTIME_OR_MANUAL**; `demo-known-good-001` remains forbidden.

## Current blockers / HOLD
- Need a Godot-capable checkout to execute v109/v110/v111.
- v110/v111 require locally restored/imported R1/R7/R8 assets, which must remain ignored by Git.
- G00-G09 need recorded candidate evidence from v112.
- G10 requires the user's final manual sanity run after G00-G09 PASS.
- Full PUZZLES/ROOMS -> WORLD compiler mapping, indirect WORLD-writer reachability and original-runtime Classic audio parity remain HOLD.

## Exact next action
On the development machine run:
`python tools/run_kg001_candidate_v112.py --fresh-checkout --promote-results`
with Godot available and local ignored room assets restored. Then run `python tools/kg001_status_v112.py`. If G00-G09 are PASS, perform `docs/KG001_MANUAL_SANITY_CHECKLIST.md` and record G10.
