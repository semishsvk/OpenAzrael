# OpenAzrael Context Bootstrap

**Current canonical checkpoint:** `v111-context-v19`
**Technical base:** `openazrael_godot_poc_v111`

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

## KG-001 quality gate
The accepted first known-good demo target is `demo-known-good-001`. It requires G00-G10 PASS, including exhaustive puzzle-state checks, transition/trigger/audio-event/save-load tests, a headless synthetic full-demo playthrough, fresh-checkout verification and final manual sanity, with zero known critical bugs and zero reproducible softlocks.

## Session close rule
A substantial session is complete only after canonical context is updated, validation passes, repository-safe changes are committed/pushed when possible, and significant milestones have an integrity-checked full snapshot.
