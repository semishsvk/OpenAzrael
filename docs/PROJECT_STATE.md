# OpenAzrael Project State

**Canonical checkpoint:** `v113-context-v21`
**Date:** 2026-09-18
**Runtime target:** Godot 4
**Active reference slice:** R1 -> R7 -> R8

## 1. Goal and architecture
OpenAzrael reconstructs *Azrael's Tear* with an evidence-first pipeline:

`original data -> forensic/import tools -> OpenAzrael IR -> Godot runtime`

Development order remains `DEMO -> faithful reconstruction -> validation -> generalization -> full game`.

## 2. Current technical base
The newest technical base is now **v113**. The context/Git/quality layer is merged forward as **v113-context-v21**.

### Graphics / rooms
- R1/R7/R8 remain the demo integration slice.
- v44 decodes all 86 demo AZF textures and validates textured R1/R7/R8 exports.
- Demo coordinate transform closure is identity XYZ at HIGH confidence since v67.
- Retail-global coordinate closure and pixel-perfect original framebuffer parity remain separate validation targets.

### Classic audio
- v58-v67 close the principal Classic spatial constants/math and demo coordinate transform.
- v68-v86 provide a shadow backend, capture/parity tooling, runtime address/signature helpers, one-command memory parity processing, and an activation-ready Godot adapter.
- `enable_unverified_classic_renderer_v86` remains false by default.
- Original-runtime pan/volume parity remains UNOBSERVED/HOLD until a genuine paused `R.EXE` memory capture plus bounded Miles trace passes the v80/v84 oracle.

### Gameplay / PUZZLES.DAT
- v87 introduces evidence-aware executable gameplay Event IR.
- v88-v100 progressively refine PUZZLES structural/action grammar.
- v101-v105 audit runtime file-open paths. Direct standard `fopen`, direct `_open`, and audited DOS open routes provide no PUZZLES read candidate. This is HIGH for the audited direct mechanisms, not proof of non-use.

### WORLD.DAT closure — v106
- Bound demo `R.EXE` object1 `0x36638` directly loads `WORLD.DAT` in binary mode.
- It reads a 30-byte header, then seven explicit count-bearing top-level sections.
- Section counts are `[1303, 12, 37, 3, 101, 8, 15]`.
- The reconstructed grammar consumes **96,425 / 96,425 bytes exactly to EOF**.
- `WORLD.DAT` direct runtime loading: VERIFIED.
- Structured runtime serialization/object database interpretation: HIGH.
- 133 unique 32-byte PUZZLES action blocks produce 0 exact matches in WORLD.DAT, excluding a simple copy/concatenation model.

### WORLD / PUZZLES sound bridge — v107
- The paired WORLD writer at object1 `0x364A8` is a real serializer, but the bound demo contains no direct rel32 CALL, direct near-JMP, or canonical LE-fixup reference to its entry in the audited classes. Indirect reachability remains HOLD.
- The live WORLD reader remains anchored through `0x1AAED` inside the central initialization path, immediately after the `SGDNAME.DAT` loader.
- PUZZLES contains 40 structurally valid opcode-`0x28` sound actions across 13 unique sound stems.
- WORLD section 6 contains 44 fixed 27-byte sound records beginning with `0x28 + printable token + NUL`.
- **38/40** PUZZLES sound records match WORLD records as a multiset and **13/13** PUZZLES sound stems occur in WORLD.
- Exact byte correspondence is VERIFIED; interpreting this as an authoring/runtime bridge for sound identity is HIGH. The complete compiler is not recovered.

### WORLD opcode-0x28 field closure — v113
- v113 upgrades the v107 sound bridge from multiset-only comparison to an order-preserving LCS: **38/40** PUZZLES sound actions align with WORLD sound records in sequence.
- The 27-byte WORLD opcode-`0x28` record now has verified runtime-consumed fields: opcode at +0, sound stem at +1, WORLD section-0 object index (u16 LE) at +13, and demo room/context id (u16 LE) at +15.
- The room mapping is 0=R1, 1=R7, 2=R8; 35/38 aligned records match the corresponding v44 XAF manifest directly and the remaining three are independently supported R7 aliases, with zero conflicts.
- The opcode handler at object1 `0x191E9` indexes the section-0 array at global `0x43890`, uses the selected object name at runtime +0x34, formats `record+1` through `%s.WAV`, and calls the dynamic 3D sample-start path at `0xD155`.
- Bytes +17..+26 are not consumed by the opcode-`0x28` handler and remain **UNKNOWN/HOLD**.
- This closes the sound-family field-level runtime bridge but does not recover the complete PUZZLES/ROOMS -> WORLD producer/compiler.

### Source-safe runtime dependency repair — context v15
- Restored exact retained-checkpoint copies of `data/gameplay_event_graph_v87.json` and `data/xaf_trigger_evidence.json`; both are required directly by the Godot runtime.
- Restored `GAMEPLAY_EVENT_GRAPH_V87.md` and its audit path.
- Replaced hard-coded `/mnt/data/.../v12` paths in `tools/extract_xaf_triggers.py` with explicit `--input-dir` / `--out` arguments.
- Added `tools/validate_demo_runtime_ir.py`, covering the five expected event graphs, three-room metadata set, four demo transitions, trigger/portal references and unit portal normals without requiring excluded binary assets.
- This closes a source-mirror defect that would otherwise make KG-001 G09 fail before asset restoration. Excluded GLB/audio/texture payloads still must be restored/generated locally for an actual Godot build.

### KG-001 state-space harness — v108
- `DemoState` now has deterministic canonical payload/JSON/SHA-256 functions with sorted key/value pairs.
- `tools/kg001_state_space_v108.py` consumes the tracked v87 Event IR and tracked trigger/transition IR.
- Exhaustive source-model result: **63 reachable states**, **123 changed transition edges**, **945 action attempts**, **0 softlocks**, **0 non-success dead ends**.
- The shortest success route is 15 actions and emits `S152V2.WAV -> S137.WAV -> S121.WAV -> 799SECDR.WAV`.
- This is source-model validation only; it does not substitute for Godot headless/runtime execution or promote forensic HOLDs.

### KG-001 headless source/runtime layer — v109
- DemoState supports schema-validated reset/restore round-trips against its canonical payload/hash.
- LegacyEvents supports capture-only logical audio instrumentation without loading excluded WAV payloads.
- `scripts/kg001_headless_runner_v109.gd` exercises the real autoload/Event-IR state path without loading `main.tscn`.
- Source contract is PASS; actual Godot runtime execution is NOT EXECUTED in this environment.
- The runner is designed to verify the v108 reference hashes and logical audio sequence before later physical room/trigger gates.

### KG-001 room/trigger runner — v110
- `scripts/kg001_room_trigger_runner_v110.gd` prepares asset-backed G04/G05 execution using the real `RoomManager`.
- It verifies all four tracked room edges, negative locked R1->R7/R8 gates, trigger centroid/outside bounds, and inventory persistence across room replacement.
- Missing R1/R7/R8 local GLBs produce `BLOCKED_MISSING_ASSETS` (exit 2), not a misleading test failure.
- Source contract is PASS; asset-backed Godot execution remains NOT EXECUTED in this environment.

### KG-001 full synthetic demo — v111
- `scripts/kg001_full_demo_runner_v111.gd` drives the complete demo through production `interact()` scripts and real RoomManager transitions.
- It uses evidence-backed trigger centroids / R8 activation center for synthetic positioning, but does not directly inject gameplay flags or puzzle nodes.
- Final hash must equal the v108 exhaustive-model success hash and the logical audio stream must equal the four Event IR sound actions.
- `tools/kg001_status_v111.py` consolidates G00-G10. Current overall state is **PRE_RUNTIME_READY** and the known-good tag remains forbidden until every gate is literal PASS.

### KG-001 candidate orchestration — v112
- `tools/run_kg001_candidate_v112.py` provides a one-command candidate workflow.
- It runs source validators, discovers Godot, imports restored local room assets, executes v109/v110/v111, checks Git cleanliness and forbidden tracked paths, and records G09 evidence.
- Temporary evidence is written only to ignored `.tmp/kg001/`; promotion into `data/tests/` is explicit and happens after the clean-checkout observation.
- `tools/kg001_status_v112.py` promotes G00-G09 only from recorded PASS evidence. G10 remains manual with a dedicated checklist/template.
- Overall state remains **AWAITING_RUNTIME_OR_MANUAL**; the known-good tag remains forbidden.

### KG-001 known-good demo gate — context v21
- The acceptance plan is now canonical at `docs/KG001_ACCEPTANCE_PLAN.md`.
- Machine-readable policy is `data/kg001_acceptance_contract.json`.
- Required gates are G00-G10: context/data/unit/puzzle/room-transition/trigger/audio-event/save-load/headless-full-demo/fresh-checkout/manual-sanity.
- Release condition: zero known critical bugs, zero reproducible softlocks and zero failed required gates.
- Passing KG-001 does not promote unrelated forensic HOLD findings.
- The build has **not** yet passed KG-001; this checkpoint formalizes the gate and repairs the context validator drift.

## 3. Current HOLD boundaries
Do not promote these as recovered original behavior yet:
- complete PUZZLES/ROOMS -> WORLD authoring/compiler mapping;
- indirect/custom PUZZLES runtime access paths not covered by the v103-v105 direct-open audit;
- indirect/computed reachability of the WORLD writer;
- real original-runtime Classic audio pan/volume parity;
- startup/default/persistence details still explicitly marked HOLD in audio evidence;
- exact reconstructed gameplay timing/motion where source semantics remain unresolved;
- retail-global coordinate transform and pixel-perfect original-vs-Godot framebuffer parity.

## 4. Current technical target
1. Run the v112 candidate runner with --fresh-checkout --promote-results, then evaluate v112 gate status and perform G10 only if G00-G09 are PASS.
2. Audit bytes +17..+26 of the WORLD opcode-0x28 record from the producer/writer side, especially `0x29E40`, while keeping their semantics UNKNOWN unless independently supported.
3. Continue tracing the complete PUZZLES/ROOMS -> WORLD producer/compiler edge; v113 closes only the sound-family runtime representation.
4. Continue Classic audio original-runtime capture parity as a separate evidence track.
5. Keep GitHub mirrors source-safe: no original commercial payloads, derived commercial-data assets, milestone archives, raw dumps, or reproducible forensic payloads containing commercial-derived bytes.

## 5. Git / backup state
GitHub private repository: `semishsvk/OpenAzrael`. Repository-safe source, tools, docs and compact context/fingerprint registries belong in Git. Original/derived binary game assets and reproducible forensic payloads remain in verified snapshots and are represented in Git only by summaries/fingerprints where appropriate.
