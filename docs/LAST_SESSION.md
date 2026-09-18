# OpenAzrael Last Session

**Checkpoint prepared:** `v113-context-v21`
**Date:** 2026-09-18

## What changed
- Advanced technical base to **v113** and canonical context to **v113-context-v21**.
- Preserved the v112 KG-001 candidate workflow unchanged: runtime execution is still pending and `demo-known-good-001` is still forbidden.
- Recovered the exact field-level runtime layout of the WORLD section-6 opcode-`0x28` 27-byte sound record.
- Verified `+13` as a u16 WORLD section-0 object index and `+15` as the demo room/context id (0=R1, 1=R7, 2=R8).
- Closed the loader -> section-0 array global `0x43890` -> opcode handler `0x191E9` -> object-name/spatial lookup -> `%s.WAV` -> dynamic 3D start `0xD155` control/data-flow chain.
- Upgraded the v107 38/40 multiset bridge to **38/40 order-preserving LCS matches**.
- Room validation gives 35 direct XAF-manifest matches plus 3 independently supported R7 aliases and zero conflicts.
- Added source-safe analyzer, result, validator and `WORLD_SOUND_RECORD_FIELDS_V113.md`.
- The v113 analyzer passes 20/20 invariants; the source-safe result validator passes and rejects raw commercial payload fields.

## Current blockers / HOLD
- KG-001 v109/v110/v111 still need execution in a Godot-capable checkout; G09 and G10 remain pending.
- Bytes +17..+26 of the 27-byte opcode-`0x28` WORLD record remain UNKNOWN/HOLD because the runtime handler does not consume them.
- The complete PUZZLES/ROOMS -> WORLD producer/compiler mapping remains HOLD.
- Indirect WORLD-writer reachability remains HOLD.
- Original-runtime Classic audio pan/volume parity remains UNOBSERVED/HOLD.

## Exact next action
In parallel:
1. on a Godot-capable development checkout run `python tools/run_kg001_candidate_v112.py --fresh-checkout --promote-results`;
2. for forensics, audit the opcode-`0x28` record tail from the producer/writer side, beginning with the matched section-6 writer path around `0x29E40`, without assigning semantics to +17..+26 unless separately proven.
