# OpenAzrael Context Bootstrap

**Current canonical checkpoint:** `v115-context-v23`
**Technical base:** `openazrael_godot_poc_v115`

This file is the mandatory entry point for every OpenAzrael work session.

## Session bootstrap order
1. Read `docs/PROJECT_STATE.md`.
2. Read `docs/DECISIONS.md`.
3. Read `docs/LAST_SESSION.md`.
4. Read the domain note(s) relevant to the task via `docs/ARTIFACT_INDEX.md`.
5. Read `data/project_context.json` for the machine-readable current state.
6. Read `docs/KG001_ACCEPTANCE_PLAN.md` for the accepted first known-good demo gate.
7. Read `docs/BACKUP_VERSIONING_POLICY.md` before repository/release/backup changes.

## Non-negotiable workflow
`DEMO -> faithful reconstruction -> validation -> generalization -> full game`

Canonical architecture:
`Original Azrael data -> importers/decoders/forensic tools -> OpenAzrael IR -> Godot runtime`

## Evidence discipline
Keep lifecycle, confidence, provenance and artifact existence separate. Never promote a HOLD merely because a tool or artifact exists. Passing KG-001 proves the defined demo build gates only; it does not automatically promote unresolved original-runtime semantics.

## Current forensic boundary
- v106 VERIFIED/HIGH: `WORLD.DAT` is directly runtime-loaded and parsed as a seven-section serialization, consuming 96,425/96,425 bytes to EOF.
- v107 VERIFIED for audited references: the paired WORLD writer at object1 `0x364A8` has no direct rel32 CALL, direct near-JMP, or canonical LE-fixup reference in the bound demo executable; indirect invocation remains HOLD.
- v107 HIGH/VERIFIED bridge: 38/40 recovered PUZZLES opcode-`0x28` sound actions have a multiset counterpart in WORLD section-6 27-byte records and all 13/13 PUZZLES sound stems occur there. This is a structural authoring/runtime bridge for sound identity, not recovery of the complete compiler.
- The full PUZZLES/ROOMS -> WORLD producer/compiler edge remains HOLD.
- Classic audio reconstruction has an activation-ready Godot adapter, but authoritative original-runtime parity remains HOLD until a genuine bounded R.EXE/Miles capture passes the v80/v84 oracle.

## WORLD sound-record field closure — v113
- v113 upgrades the v107 opcode-0x28 bridge from multiset identity to **38/40 order-preserving PUZZLES -> WORLD matches**.
- WORLD section-6 27-byte sound records now have verified runtime-consumed fields: opcode at +0, sound stem at +1, WORLD section-0 object index (u16 LE) at +13, and demo room/context id (u16 LE) at +15.
- Demo room mapping is 0=R1, 1=R7, 2=R8, supported by 35 direct XAF-manifest matches plus 3 independently supported R7 aliases and zero conflicts.
- Opcode-0x28 runtime path resolves the section-0 object through global 0x43890, uses the object name at runtime +0x34, formats record+1 as %s.WAV, and calls the dynamic 3D sample-start path at 0xD155.
- Bytes +17..+26 remain UNKNOWN/HOLD because the opcode-0x28 handler does not consume them.
- The complete PUZZLES/ROOMS -> WORLD producer/compiler remains HOLD.

## WORLD section-6 opaque serializer closure — v114
- v114 verifies the reciprocal section-6 chains: reader `0x369DC -> 0x29E98 -> 0x29EEA -> 0x29CF4 -> 0x29D2E -> 0x29638` and writer `0x3661A -> 0x29E40 -> 0x29E87 -> 0x29D74 -> 0x29DA5 -> 0x2972C`.
- The nested reader allocates and reads 37-byte (`0x25`) and 27-byte (`0x1B`) records wholesale; the matched writer writes the same fixed blobs wholesale. The serializer is therefore field-opaque.
- The bound WORLD contains 400 27-byte and 387 37-byte section-6 records; 44 are opcode-0x28 sound records.
- Sound tails +17..+26 have 41 unique values across 44 records. All 7/7 duplicated (stem, section-0 object, room) groups vary in their tail; the 12 `797tap -> tapframe2 -> R8` records have 12 different tails.
- The only audited direct `mov eax,0x1B` -> allocator `0x20C00` pattern is the WORLD reader at `0x29703 -> 0x29712`; alternate construction mechanisms remain possible.
- Exact tail origin/meaning remains UNKNOWN/HOLD. The next target is record construction/mutation/copy logic, not the serializer.

## WORLD action-record runtime lifecycle — v115
- The 27-byte action-list insert helper `0x295B0` and 37-byte sibling-list insert helper `0x295F4` each have exactly one direct caller in object1, both inside the WORLD nested reader `0x29638`, in the audited direct-call class.
- The only audited direct immediate `malloc(27)`-style pattern remains the WORLD reader allocation `0x29703 -> 0x29712`.
- On condition success, `0x2990C` schedules only a **6-byte shallow group**: u16 action count copied from nested-object +6 plus the original action-pointer-array address copied from +8.
- Dispatcher `0x18698` walks those 6-byte entries, follows the original pointer array and dispatches the original 27-byte record pointer in place.
- No action-record copy/normalization step is present between WORLD deserialization and opcode execution in this audited runtime path; opcode-0x28 also does not mutate the record before consuming its fields.
- Therefore the v114 +17..+26 residue is already serialized upstream and survives unchanged into dispatch. Its authoring origin remains UNKNOWN/HOLD.

## Source-safe runtime IR
- `data/gameplay_event_graph_v87.json` and `data/xaf_trigger_evidence.json` are compact runtime IR/evidence metadata and are tracked in Git. Binary rooms, textures and audio remain excluded.
- `tools/extract_xaf_triggers.py` is portable and regenerates the trigger IR from a local corrected-GLB corpus via explicit CLI paths.

## KG-001 v108 state-space layer
- Canonical persistent DemoState serialization/hash is implemented in `scripts/demo_state.gd`.
- `tools/kg001_state_space_v108.py` exhaustively explores the current source-safe demo logic using the shared Event IR and trigger/transition IR.
- Current source-model result: 63 reachable states, 123 changed edges, 0 softlocks, 0 non-success dead ends. Godot runtime execution remains required before KG-001 can pass.

## KG-001 v109 headless layer
- DemoState now supports reset/restore round-trip against the canonical payload/hash.
- LegacyEvents has a capture-only logical audio mode that avoids loading excluded WAV assets.
- `scripts/kg001_headless_runner_v109.gd` tests the real autoload/Event-IR state path without loading `main.tscn`.
- Source contract: PASS. Godot runtime execution: NOT EXECUTED in this environment.

## KG-001 v110 room/trigger layer
- `scripts/kg001_room_trigger_runner_v110.gd` prepares asset-backed G04/G05 tests using the real RoomManager trigger implementation.
- It covers all four tracked transitions, both R1 locked negative gates, trigger inside/outside bounds and persistence across room replacement.
- Missing local room assets are reported as BLOCKED_MISSING_ASSETS rather than FAIL.
- Source contract: PASS. Godot asset-backed execution: NOT EXECUTED here.

## KG-001 v111 full-demo layer
- `scripts/kg001_full_demo_runner_v111.gd` executes the complete synthetic demo path through production interaction scripts and real RoomManager transitions.
- Direct gameplay flag/puzzle-node injection is forbidden by the source validator.
- `tools/kg001_status_v111.py` consolidates G00-G10 and only literal PASS for every gate permits the known-good tag.
- Overall status: PRE_RUNTIME_READY. v109/v110/v111 Godot execution remains pending.

## KG-001 v112 candidate workflow
- `tools/run_kg001_candidate_v112.py` runs source validators plus v109/v110/v111 and can record G09 clean-checkout evidence.
- Temporary evidence is kept in ignored `.tmp/kg001/`; promotion into `data/tests/` is explicit.
- `tools/kg001_status_v112.py` upgrades gates only from recorded PASS evidence; G10 remains manual.
- G10 checklist/template are ready. Overall status remains AWAITING_RUNTIME_OR_MANUAL and the tag is not allowed.

## KG-001 quality gate
The accepted first known-good demo target is `demo-known-good-001`. It requires G00-G10 PASS, including exhaustive puzzle-state checks, transition/trigger/audio-event/save-load tests, a headless synthetic full-demo playthrough, fresh-checkout verification and final manual sanity, with zero known critical bugs and zero reproducible softlocks.

## Session close rule
A substantial session is complete only after canonical context is updated, validation passes, repository-safe changes are committed/pushed when possible, and significant milestones have an integrity-checked full snapshot.
