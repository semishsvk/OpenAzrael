# OpenAzrael Last Session

**Checkpoint prepared:** `v114-context-v22`
**Date:** 2026-09-18

## What changed
- Advanced technical base to **v114** and canonical context to **v114-context-v22**.
- Preserved the v112 KG-001 candidate workflow unchanged: runtime execution is still pending and `demo-known-good-001` remains forbidden.
- Preserved v113 field-level opcode-0x28 closure: sound stem at +1, section-0 object index u16 at +13, demo room/context id u16 at +15.
- Closed the reciprocal section-6 serialization paths:
  - reader: `0x369DC -> 0x29E98 -> 0x29EEA -> 0x29CF4 -> 0x29D2E -> 0x29638`;
  - writer: `0x3661A -> 0x29E40 -> 0x29E87 -> 0x29D74 -> 0x29DA5 -> 0x2972C`.
- Verified that 37-byte and 27-byte section-6 records are read/written wholesale as opaque fixed-size blobs.
- Audited all 44 opcode-0x28 records: +17..+26 has 41 unique tails; 40/44 are non-zero.
- All 7 duplicated (sound stem, section-0 object, room) groups vary in their tail. The 12 797tap/tapframe2/R8 records have 12 unique tails.
- The only direct immediate `mov eax,0x1B` -> allocator `0x20C00` pattern in object1 is the WORLD reader allocation at `0x29703 -> 0x29712`.
- Added source-safe analyzer/result/validator and `WORLD_SOUND_SERIALIZER_V114.md`; analyzer passes 29/29 checks.
- Tail bytes remain UNKNOWN/HOLD; no padding/pointer/uninitialized-memory label is asserted.

## Current blockers / HOLD
- KG-001 v109/v110/v111 still need execution in a Godot-capable checkout; G09 and G10 remain pending.
- Exact origin/meaning of bytes +17..+26 remains UNKNOWN/HOLD.
- The complete PUZZLES/ROOMS -> WORLD producer/compiler mapping remains HOLD.
- Indirect WORLD-writer entry reachability remains HOLD.
- Original-runtime Classic audio pan/volume parity remains UNOBSERVED/HOLD.

## Exact next action
In parallel:
1. on a Godot-capable development checkout run `python tools/run_kg001_candidate_v112.py --fresh-checkout --promote-results`;
2. for forensics, search constructors, mutators and copy paths for the 27-byte action-record family, especially writes into +17..+26. The serializer itself is now closed as opaque.
