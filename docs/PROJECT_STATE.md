# OpenAzrael Project State

**Canonical checkpoint:** `v116-context-v31`
**Date:** 2026-09-19
**Runtime target:** Godot 4
**Active reference slice:** R1 -> R7 -> R8

## 1. Goal and architecture
OpenAzrael reconstructs *Azrael's Tear* with an evidence-first pipeline:

`original data -> forensic/import tools -> OpenAzrael IR -> Godot runtime`

Development order remains `DEMO -> faithful reconstruction -> validation -> generalization -> full game`.

## 2. Current technical base
The newest technical base is now **v116**. The context/Git/quality layer is merged forward as **v116-context-v31**.

## 3. Immediate execution priority
Issues #6, #9 and #11 are the active KG-001 release blockers. Candidate 1 showed the player falling through the R1 floor, produced no audible audio, and exposed pink/magenta where legacy cutout textures should be transparent. Candidate 2 / v30 combines the two-sided collision repair, physical-audio readiness, and a conservative `# + quantized-magenta` color-key pipeline that preserves RGBA into GLB `MASK` materials. All fixes are source-ready but still require restored-asset/runtime and human confirmation.

The current priority is the corrected **KG-001 Candidate 2** runtime cycle on a Godot-capable checkout: restore ignored assets with the v30 pipeline, run the v112 fresh-checkout workflow, require floor/audio/color-key regressions plus G00-G09 PASS, then complete G10 through the normal graphical build. F11 can capture any discovered defect into a source-safe diagnostic ZIP for GitHub Issues.

Localization runtime work and the deferred v117 forensic copy/mutator audit follow the first clean Candidate 2 runtime/manual cycle; neither is part of the current blocker-fix scope.

### Graphics / rooms
- R1/R7/R8 remain the demo integration slice.
- v44 decodes all 86 demo AZF textures and validates textured R1/R7/R8 exports.
- Demo coordinate transform closure is identity XYZ at HIGH confidence since v67.
- Retail-global coordinate closure and pixel-perfect original framebuffer parity remain separate validation targets.

### Legacy color-key textures — Issue #11
- AZF output remains RGB for ordinary textures.
- Only `#` filenames with observed quantized magenta key pixels are converted to RGBA.
- Shared key threshold: R/B >= 248 and G <= 12; keyed pixels use alpha 0 with zeroed RGB.
- XAF->GLB preserves the mask as PBR alpha mode MASK / cutoff 0.5.
- Source-safe synthetic regression plus restored-corpus audit is wired into the Candidate runner.
- Complete original renderer transparency/blending semantics remain HOLD.

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

### WORLD section-6 opaque serializer closure — v114
- The reciprocal section-6 serializer path is now closed: reader `0x29E98 -> 0x29CF4 -> 0x29638`, writer `0x29E40 -> 0x29D74 -> 0x2972C`.
- The nested 37-byte and 27-byte record families are both read and written wholesale as fixed memory blobs. The serializer itself does not decode the v113 sound fields or the remaining bytes.
- Section 6 contains 400 x 27-byte records and 387 x 37-byte records; 44 of the 27-byte records are opcode-0x28 sound actions.
- Across those 44 sound records, +17..+26 has 41 unique values; all 7 duplicated runtime-equivalent (stem/object/room) groups vary in their tail. The 12 797tap/tapframe2/R8 records have 12 unique tails.
- A conservative immediate-allocation audit finds one direct malloc(27)-style pattern and it is the WORLD reader itself. Variable/generic/alternate construction remains possible.
- Tail origin/meaning remains **UNKNOWN/HOLD**. Serializer analysis cannot promote it; the next target is record construction/mutation/copy behavior.

### WORLD action-record lifecycle — v115
- The runtime lifecycle of section-6 27-byte action records is now closed for the audited load/schedule/dispatch path.
- Direct insert helpers `0x295B0` (27-byte list) and `0x295F4` (37-byte list) each have one direct caller, both in WORLD reader `0x29638`; the only audited direct immediate 27-byte allocation is also the reader.
- Condition scheduling at `0x2990C` creates a 6-byte pending group containing only the original action count and pointer-array address.
- Dispatcher `0x18698` follows that original pointer array and dispatches the original record pointer in place. No hidden record copy/normalization occurs in this path.
- This proves the v114 residue +17..+26 is already in serialized WORLD and is not manufactured by the audited runtime path; exact upstream authoring meaning remains UNKNOWN/HOLD.
- The complete PUZZLES/ROOMS -> WORLD producer/compiler remains HOLD.

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

### Localization architecture — approved
- External, versioned language packs are now the canonical localization direction.
- Runtime/UI will use immutable semantic IDs rather than editable English sentences as keys.
- Translator-facing source format is POT/PO; English ships in the base game as mandatory fallback.
- Release packs use `openazrael-<locale>.pck` and a validated manifest/string revision.
- External packs must be mounted with resource replacement disabled and may only expose a dedicated localization namespace.
- The future `LocalizationManager` owns discovery/validation/locale switching only; it does not own gameplay state.
- The format is extensible to locale fonts, subtitles and optional localized voice assets.
- Pseudolocalization, missing-ID checks, Unicode coverage and deterministic pack-building are required implementation tests.
- Runtime implementation is **DEFERRED until after the first KG-001 Candidate 2 runtime/manual cycle**, so this approval does not perturb the current test candidate.
- Canonical design: `docs/LOCALIZATION_ARCHITECTURE.md`.

### KG-001 Candidate 2 diagnostics — v116
- The first real Godot integration candidate is now source-ready as **KG-001 Candidate 2**.
- Added `CandidateDiagnostics` autoload with structured JSONL event logging, canonical state hashes and F10 state dumps.
- Added F6 authored trigger-volume visualization and an F7 diagnostic HUD showing room, player XYZ, flags, puzzle nodes, value keys, last trigger, last event and last logical audio.
- Existing F8 audio debug and F9 parity capture are deliberately preserved.
- Room GLBs are runtime-loaded after explicit resource preflight rather than preloaded at script parse time, giving deterministic missing-asset diagnostics.
- Non-headless preflight also requires the four golden Event-IR WAV assets used by the accepted demo route; headless capture-only tests do not.
- `tools/validate_candidate_diagnostics_v116.py` is included in the v112 one-command candidate source suite.
- Source contract: **PASS**. Godot runtime execution: **NOT EXECUTED** in the current environment.
- The earlier uncommitted static producer/copy experiment is deferred and renumbered to v117.

### KG-001 known-good demo gate — context v24
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
1. Restore Candidate 2 assets with the v30 color-key pipeline, run the v112 candidate runner with --fresh-checkout --promote-results, require v109/v110/v111/audio-v116 plus texture color-key validation PASS, then complete G10 only after floor collision, audible audio and visual transparency are clean.
2. Audit generic 27-byte copy paths, direct/indirect stores into action-record +17..+26, and variable/generic allocation paths outside the now-closed load/schedule/dispatch lifecycle.
3. Continue tracing the complete PUZZLES/ROOMS -> WORLD producer/compiler edge; v113-v114 close only the sound-family runtime representation and serialization behavior.
4. Continue Classic audio original-runtime capture parity as a separate evidence track.
5. Keep GitHub mirrors source-safe: no original commercial payloads, derived commercial-data assets, milestone archives, raw dumps, or reproducible forensic payloads containing commercial-derived bytes.

## 5. Git / backup state
GitHub private repository: `semishsvk/OpenAzrael`. Repository-safe source, tools, docs and compact context/fingerprint registries belong in Git. Original/derived binary game assets and reproducible forensic payloads remain in verified snapshots and are represented in Git only by summaries/fingerprints where appropriate.
