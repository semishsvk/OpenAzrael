# OpenAzrael Project State

**Canonical checkpoint:** `v107-context-v14`
**Date:** 2026-09-18
**Runtime target:** Godot 4
**Active reference slice:** R1 -> R7 -> R8

## 1. Goal and architecture
OpenAzrael reconstructs *Azrael's Tear* with an evidence-first pipeline:

`original data -> forensic/import tools -> OpenAzrael IR -> Godot runtime`

Development order remains `DEMO -> faithful reconstruction -> validation -> generalization -> full game`.

## 2. Current technical base
The newest technical base remains **v107**. The context/Git/quality layer is merged forward as **v107-context-v14**.

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

### KG-001 known-good demo gate — context v14
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
1. Implement the executable KG-001 automated harness, starting with deterministic state serialization/hash plus puzzle-state exploration.
2. Reverse the 27-byte WORLD sound-action record and the section-6 reader chain (`0x29E98 -> 0x29CF4 -> 0x29638`).
3. Identify which numeric/runtime fields replace the second PUZZLES operand/state token.
4. Continue Classic audio original-runtime capture parity as a separate evidence track.
5. Keep GitHub mirrors source-safe: no original commercial payloads, derived commercial-data assets, milestone archives, raw dumps, or reproducible forensic payloads containing commercial-derived bytes.

## 5. Git / backup state
GitHub private repository: `semishsvk/OpenAzrael`. Repository-safe source, tools, docs and compact context/fingerprint registries belong in Git. Original/derived binary game assets and reproducible forensic payloads remain in verified snapshots and are represented in Git only by summaries/fingerprints where appropriate.
