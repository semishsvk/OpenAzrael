# OpenAzrael Context Bootstrap

## Candidate 2 Windows execution — 2026-09-20

**KG-001 Candidate 2 / v116-context-v32: G00-G09 PASS; G10 PENDING_MANUAL_USER.**
Tested source `89ccf775dfd6abc21e6bc69f344fe2d349b4dd70`, Godot `4.7.2.stable.official.ed1daf0bf`.
The clean-checkout suite passed source validation, asset import, v109, v110,
v111 and audio-v116 (62 checks). The exported Windows EXE passed headless and
graphical smoke tests. Instrumented exported-PCK checks passed real floor
support in R1/R7/R8, nonzero Master audio output, cutout materials and F11 ZIP
capture without a gameplay-state hash change. Supplied Sigil icons are verified
inside the executable. Some headless scene tests report non-fatal ObjectDB
cleanup warnings; there are no ERROR or SCRIPT ERROR lines in the passing runs.

Additional integration fixes preserve the authored invisible R8/Object01
entrance support collision, repair empty ambient WAV loop ranges, and retain
Godot numeric typing and runner error handling. The v32 indexed palette rule
preserves the single near-magenta non-key pixel in BLOOS4#.

Candidate 1 manual failure remains historical evidence. Issues #6, #9 and #11
await human retest and remain release blockers. No `demo-known-good-001` tag
is allowed or created. Original Miles parity and complete original renderer
transparency semantics remain HOLD. See `docs/CANDIDATE2_WINDOWS.md` and
`data/tests/kg001_candidate2_windows.json` for details.

**Current canonical checkpoint:** `v116-context-v32`
**Technical base:** `openazrael_godot_poc_v116`

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

### Non-negotiable room geometry fidelity
Every playable room must use the **complete original source-derived geometry**. Partial imports, simplified rooms, invented/approximated architecture, AI-generated runtime geometry and substitute meshes are forbidden. Missing geometry is fail-closed (`BLOCKED_MISSING_SOURCE_GEOMETRY`) and is a critical build defect. Engine compatibility fixes may not change authored shape. Candidate export/KG promotion requires geometry parity for every included room. See ADR-033/ADR-034, `docs/SOURCE_GEOMETRY_FIDELITY.md` and the v122-v131 fidelity closure: geometry, visibility, material/UV, transforms, graphical direct-vs-runtime census, all-reachable-state visibility, packaged EXE/PCK parity, portal closure, physical interaction reachability and per-room forensic reporting.

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

## Immediate execution priority
- Candidate 2 automated Windows evidence is retained as historical evidence, but its later manual traversal failure makes it non-promotable and stale for current source.
- Candidate 3 is the active integration target. Its source hardening includes natural portal-spawn clearance, two-sided legacy collision, winding-safe near-to-far stair step-up with diagnostic trace, exact-demo well+tongs ordering, physical triggered-audio probes, indexed color-key masking, and a KEYHOLE#-only vertical UV compatibility correction.
- Candidate 3 export is fail-closed: exact Git HEAD, Godot version, candidate/fresh evidence hashes, **exact runtime asset path set**, per-asset hashes and exported-EXE startup smoke must all match before a PASS export receipt may exist.
- First require source CI PASS, then run the asset-backed Candidate 3 preflight and require v109/v110/v111/audio-v116/physical-v117/well-tongs-v118 literal PASS at the exact build SHA.
- G10 must then confirm R1 floor traversal, both R8 stair profiles, audible ambient/triggered audio, well+tongs, cutout transparency, upright KEYHOLE orientation, full demo route and save/load. Keep all release blockers and `demo-known-good-001` blocked until that evidence exists.

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
- v28 adds the Issue #6 regression: all generated legacy concave collision shapes must be two-sided, a real downward physics probe must find the R1 floor, and the real player capsule must settle with `is_on_floor()` instead of falling through.
- Missing local room assets are reported as BLOCKED_MISSING_ASSETS rather than FAIL.
- Source contract: PASS. Godot asset-backed execution: NOT EXECUTED here.

## KG-001 v111 full-demo layer
- `scripts/kg001_full_demo_runner_v111.gd` executes the complete synthetic demo path through production interaction scripts and real RoomManager transitions.
- Direct gameplay flag/puzzle-node injection is forbidden by the source validator.
- `tools/kg001_status_v111.py` consolidates G00-G10 and only literal PASS for every gate permits the known-good tag.
- Overall status: G00-G09 PASS. v109/v110/v111/audio-v116 Godot execution passed; G10 remains pending.

## KG-001 v112 candidate workflow
- `tools/run_kg001_candidate_v112.py` runs source validators plus v109/v110/v111 and the audio-v116 physical-readiness regression, then can record G09 clean-checkout evidence.
- Temporary evidence is kept in ignored `.tmp/kg001/`; promotion into `data/tests/` is explicit.
- `tools/kg001_status_v112.py` requires both the logical audio golden stream and audio-v116 physical readiness for G06, and independently blocks the known-good tag while a recorded `kg001_release_blocked_by_*` defect remains.
- G10 remains manual and must confirm actual audibility; an automated Godot player reporting `playing=true` is not human-listening evidence.

## KG-001 physical audio readiness — v116 / Issue #9
- Source-safe ambient metadata is tracked as `data/audio/legacy_world_ir.json`; original WAV payloads remain Git-ignored and are restored locally through `tools/restore_candidate_assets.py`.
- The recovered demo ambient topology is R1=2 emitters, R7=3, R8=2, using `S174ELP1.WAV`, `S174ELP2.WAV` and `S186.WAV`.
- `scripts/legacy_ambient_audio.gd` falls back from a null `godot_position` to the preserved legacy position.
- `LegacyEvents` tracks real physical Event-IR `AudioStreamPlayer` instances in addition to the logical golden stream.
- `scripts/kg001_audio_runtime_runner_v116.gd` and `tools/validate_kg001_audio_runtime_v116.py` form the G06 physical-readiness layer.
- Automated readiness does not prove speaker/headphone audibility and does not promote original Miles pan/volume parity. Human audibility is G10; Miles parity remains HOLD.

## KG-001 legacy color-key compatibility — v116 / Issue #11
- A real metadata-only audit of all 86 ATDEMO AZFs disproved the broader v31 uniqueness assumption: `BLOOS4#.AZF` uses key index 5 plus one near-magenta non-key pixel at index 9.
- Candidate 2 therefore re-froze at v32 with the source-palette sentinel rule: exactly one used entry with raw R=255, B=255, G<=8 in every `#` texture; no non-`#` texture uses that sentinel.
- The audit is bound by demo-archive and per-texture SHA-256 in `data/tests/kg001_colorkey_corpus_audit_v116.json`.
- The Classic AZF decoder applies a conservative shared rule: only texture names containing `#` with exactly one used raw palette sentinel (R=255/B=255/G<=8) are converted to binary alpha.
- The broader quantized-magenta range is diagnostic only. Alpha is selected by the exact audited source palette index; all other indices remain opaque.
- The XAF->GLB exporter preserves RGBA and emits a PBR `MASK` material with alpha cutoff 0.5 instead of converting the image back to RGB.
- The demo source-safe contract tracks ten `#` texture names. R1 known regressions are `KEYHOLE#` and `TONG6 -> MINETON#`.
- `tools/validate_kg001_texture_colorkey_v116.py` always runs source-safe synthetic checks and automatically audits the restored 86-texture corpus/R1 manifest when local assets are present.
- This is a presentation compatibility rule, not proof of complete original renderer transparency/blending semantics; that broader claim remains HOLD.

## KG-001 Candidate 3 diagnostics — v116
- Candidate 3 is the active diagnostic integration target; Candidate 2 Windows automation remains historical evidence only.
- `CandidateDiagnostics` remains observational and records state/event telemetry without changing puzzle semantics.
- F6 toggles trigger volumes; F7 toggles the Candidate HUD; F8 shows ambient emitters plus Master-bus and physical Event-IR player state; F9 preserves parity capture; F10 writes canonical state; F11 captures a source-safe bug package.
- Non-headless builds append JSONL events to `user://openazrael_candidate3_events.jsonl`.
- Core room/IR resources include source-safe `data/audio/legacy_world_ir.json`. A graphical Candidate additionally requires four Event-IR WAVs plus three recovered ambient WAVs.
- `scripts/kg001_audio_runtime_runner_v116.gd` checks resource loading, Master-bus state, ambient counts R1=2/R7=3/R8=2, ambient `playing` state and an Event-IR physical player.
- Source contracts are wired for Candidate 3; current-head runtime/preflight and manual confirmation remain pending.

## Approved localization architecture
- Localization uses stable semantic IDs over a separate String IR; editable English text is not the identifier.
- English is the mandatory built-in fallback.
- Translator-facing catalogs use POT/PO.
- Distributable language packs are external versioned PCKs with manifests and dedicated namespaces.
- External PCKs must not replace core resources.
- Optional future payloads include fonts, subtitle metadata and localized voice.
- Runtime implementation is deferred until after the first clean KG-001 Candidate 3 runtime/manual cycle.
- See `docs/LOCALIZATION_ARCHITECTURE.md` and ADR-024.

## KG-001 quality gate
The accepted first known-good demo target is `demo-known-good-001`. It requires G00-G10 PASS, including logical and physical audio readiness plus a clean human audibility check. The tag is additionally blocked while any recorded KG-001 release blocker remains.

## Session close rule
A substantial session is complete only after canonical context is updated, validation passes, repository-safe changes are committed/pushed when possible, and significant milestones have an integrity-checked full snapshot.


### Control rendering invariant
All future validation renders are produced as a paired set from the same source-exact geometry/state/camera: **ORIGINAL-1996** lighting and **NEUTRAL-QA** lighting. Original lighting may only use recovered/documented 1996 renderer evidence; when unavailable it is marked `ORIGINAL-LIGHTING-PENDING` and is never approximated. See `docs/CONTROL_RENDERING_STANDARD.md`.
