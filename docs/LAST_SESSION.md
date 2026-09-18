# OpenAzrael Last Session

**Checkpoint prepared:** `v111-context-v19`
**Date:** 2026-09-18

## What changed
- Advanced technical base to **v111** and canonical context to **v111-context-v19**.
- Preserved v108 exhaustive state-space result: 63 reachable states, 123 changed transitions, 0 modeled softlocks.
- Preserved v109 save/reset/restore + capture-only Event IR headless runner; source contract PASS, Godot runtime NOT EXECUTED.
- Preserved v110 asset-backed room/trigger runner; source contract PASS, Godot runtime NOT EXECUTED.
- Added `scripts/kg001_full_demo_runner_v111.gd`, a no-human full demo route using production interaction scripts and real RoomManager transitions.
- v111 path: Tongs -> Door1 -> R7 -> Well Key -> lever/wheel/lever -> R1 -> Door2 -> R8 -> Lens -> Bible lens placement -> zxplate optical activation -> secret door -> Shield.
- v111 validates final canonical hash and logical Event IR audio stream; its validator rejects direct state.set_flag / set_puzzle_node injection.
- Added `tools/kg001_status_v111.py` and a consolidated G00-G10 snapshot. Overall status is **PRE_RUNTIME_READY**; the final tag is not allowed.
- Fixed a static-typing risk in the runner by using dynamic activation-center lookup.

## Current blockers / HOLD
- v109/v110/v111 still require actual execution in a Godot-capable checkout.
- v110/v111 additionally require locally restored/imported R1/R7/R8 GLBs.
- G00/G01 release validators need recorded execution in the candidate checkout.
- G09 fresh-checkout verification and G10 manual sanity are still pending.
- Full PUZZLES/ROOMS -> WORLD compiler mapping, indirect WORLD-writer reachability and original-runtime Classic audio parity remain HOLD.

## Exact next action
Execute v109 first in a source-only Godot checkout. Then restore/import R1/R7/R8 and execute v110 and v111. Capture their JSON result lines into the expected runtime result files, run G00/G01, then perform G09 fresh-checkout verification.
