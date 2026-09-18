# OpenAzrael Last Session

**Checkpoint prepared:** `v115-context-v23`
**Date:** 2026-09-18

## What changed
- Advanced technical base to **v115** and canonical context to **v115-context-v23**.
- KG-001 v112 candidate workflow remains unchanged and still requires a Godot-capable checkout; `demo-known-good-001` remains forbidden.
- Preserved v113 verified opcode-0x28 fields and v114 opaque serializer closure.
- Closed the bound runtime lifecycle of 27-byte action records after WORLD deserialization.
- 27-byte insert helper `0x295B0` has one direct caller (`0x296EC`); 37-byte helper `0x295F4` has one direct caller (`0x2968A`), both in the WORLD reader.
- The only audited direct immediate `malloc(27)` pattern remains `0x29703 -> 0x29712`.
- Condition scheduling at `0x2990C` creates a 6-byte pending group: u16 count from nested object +6 plus pointer-array address from +8.
- Dispatcher `0x18698` follows the original pointer array and dispatches the original 27-byte record pointer in place.
- No copy/normalization stage exists in the audited WORLD-load -> scheduling -> dispatch path; the opcode-0x28 handler does not mutate the record before consuming it.
- Therefore +17..+26 is serialized upstream and survives unchanged to dispatch; its exact authoring origin remains UNKNOWN/HOLD.
- Added source-safe v115 analyzer/result/validator/documentation; analyzer passes 20/20 invariants and validator PASS.

## Current blockers / HOLD
- KG-001 v109/v110/v111 runtime execution, G09 fresh checkout and G10 manual sanity remain pending.
- Exact upstream origin/meaning of WORLD action-record +17..+26 remains UNKNOWN/HOLD.
- Complete PUZZLES/ROOMS -> WORLD producer/compiler remains HOLD.
- Indirect/computed WORLD-writer reachability remains HOLD.
- Original-runtime Classic audio pan/volume parity remains UNOBSERVED/HOLD.

## Exact next action
In parallel:
1. on a Godot-capable development checkout run `python tools/run_kg001_candidate_v112.py --fresh-checkout --promote-results`;
2. audit static generic 27-byte copies, writes into +17..+26, variable/generic allocation paths, and stronger indirect/computed references around the WORLD producer/writer side.
