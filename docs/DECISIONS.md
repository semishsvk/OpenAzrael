# OpenAzrael Decision Log

This file records durable architectural decisions. Do not silently reverse an ACCEPTED decision; append a superseding ADR instead.

## ADR-001 — Godot 4 runtime
**Status:** ACCEPTED  
OpenAzrael uses Godot 4 as the target runtime. Reverse-engineering and IR layers remain as engine-independent as practical.

## ADR-002 — Original data -> IR -> runtime
**Status:** ACCEPTED  
Original game data is not treated as hand-authored Godot scene content. Importers/decoders produce a clean OpenAzrael IR, which the runtime consumes.

## ADR-003 — Demo first
**Status:** ACCEPTED  
Development order is `demo -> faithful reconstruction -> validation -> generalization -> full game`. The demo becomes a reusable engine reference, not disposable prototype code.

## ADR-004 — Evidence and runtime are separate
**Status:** ACCEPTED  
Original evidence, derived calibration, reconstruction assumptions and runtime defaults must remain distinguishable. Runtime usefulness is not proof of original semantics.

## ADR-005 — No promotion from hypothesis to fact without validation
**Status:** ACCEPTED  
`ANALYZED`, `IMPLEMENTED`, `TESTED`, `VERIFIED`, confidence and provenance are separate dimensions. Experimental or HOLD findings cannot become canonical Classic behavior solely because they appear plausible.

## ADR-006 — Shared gameplay, switchable presentation
**Status:** ACCEPTED  
Classic, Enhanced and Remastered presentation modes share the same recovered world/puzzle/gameplay logic and identifiers.

## ADR-007 — Preserve original coordinates
**Status:** ACCEPTED  
Source coordinates remain immutable evidence. Any Godot conversion/calibration is stored separately as derived output and scoped to the corpus for which it was validated.

## ADR-008 — Audio reconstruction is data-driven
**Status:** ACCEPTED  
Audio assets, mappings and emitter coordinates are represented in a SoundDatabase/world IR. Classic and Enhanced renderers operate on this common source instead of embedding room-specific guesses into scene scripts.

## ADR-009 — Session handoff is part of the repository
**Status:** ACCEPTED  
Every substantial session begins with `OPENAZRAEL_CONTEXT.md` and ends by updating `PROJECT_STATE.md`, `LAST_SESSION.md`, artifact references and machine-readable context where relevant.

## ADR-010 — Preserve v31 relocation gate
**Status:** ACCEPTED  
LE record/source parsing can be promoted independently, but loader relocation semantics, trusted relocated image/xrefs and Miles call sites remain HOLD until independent relocation invariants converge.

## ADR-011 — Git is source history, not full backup
**Status:** ACCEPTED  
Repository history contains code, documentation, evidence metadata and reproducible tooling. Full working-tree backup is a separate system and intentionally includes local source evidence excluded from Git.

## ADR-012 — Original commercial payloads stay outside Git by default
**Status:** ACCEPTED  
Raw/original Azrael's Tear payloads, installation media, extracted original media and executable/dump material are excluded from the default repository boundary. Repository-safe fingerprints may identify the local corpus without committing the payload.

## ADR-013 — Verified milestones require recoverability
**Status:** ACCEPTED  
A significant verified checkpoint is not operationally complete until canonical context is current, validation passes, the coherent change is committed, and—when a private remote is configured—pushed. Important milestone/release checkpoints also require an integrity-verified full snapshot.

## ADR-014 — Backup target follows 3-2-1 principles
**Status:** ACCEPTED  
Maintain multiple copies on distinct storage classes, including an off-site copy and periodically disconnected offline storage. Chat/library ZIPs are convenience checkpoints, not the sole backup.

## ADR-015 — Coherent direct-call evidence can advance independently of global relocation
**Status:** ACCEPTED  
When raw executable control flow and direct relative CALLs are independently coherent, those local findings may be promoted at their own confidence level without claiming that global LE loader relocation semantics are solved. v37-v38 use this separation.

## ADR-016 — Unrelocated address placeholders are not runtime constants
**Status:** ACCEPTED  
An operand value in the raw/unrelocated object image must not be dereferenced as if it were a runtime data address when the apparent target overlaps coherent code or otherwise lacks independent relocation proof. v39 specifically withdraws raw-constant decoding at `0x1954..0x1994` and `0x615E`.

## ADR-017 — Exact Classic 3D audio waits for independently validated constants
**Status:** ACCEPTED  
The v39 symbolic formula is canonical forensic metadata, but the Classic renderer must not bake in guessed `K_DISTANCE`, global-volume or angular constants. Exact implementation requires independently recovered runtime values plus regression/golden-vector validation.

## ADR-018 — Quarantine legacy operand-level LE xref semantics
**Status:** ACCEPTED  
v52-v56 supersede semantic use of the v27-v36 source/xref mapping for 3D-core operand binding. The corpus remains useful structurally, but it must not bind runtime constants/APIs until a replacement mapping passes the eight exact disp32 anchors.

## ADR-019 — Independent evidence may recover constants without global relocation closure
**Status:** ACCEPTED  
The v58 qword-lattice recovery is canonical because independent literal ordering plus instruction semantics agree. `K_DISTANCE=15000` and the angular/pan constants may advance at HIGH confidence even while global LE relocation semantics remain HOLD.

## ADR-020 — Reference math is canonical before runtime parity
**Status:** ACCEPTED  
v59 angle-domain pan and distance-domain attenuation reference functions/golden vectors are canonical forensic models. They do not by themselves prove complete XYZ-to-output runtime parity.

## ADR-021 — Ambient loop ABI correction supersedes older loop-count claims
**Status:** ACCEPTED  
v50 supersedes v46's loop-count 0 interpretation and v49's HOLD classification of literal 1000. The numeric argument reaching `AIL_set_sample_loop_count` is 1000 at HIGH confidence; the exact Miles semantic meaning of that numeric value remains HOLD.

## ADR-022 — Master volume is distinct from the spatial gain ceiling
**Status:** ACCEPTED  
The value 99 is the spatial gain ceiling/normalizer, not the Classic master-volume default. v60 establishes an independent UI path mapping 0..87 to a runtime master-volume range 0..127; startup/default/persistence remains HOLD.



## ADR-015 — Separate helper identity from caller-level heading semantics (v63)
**Decision:** Treat the post-FPATAN constant `pi/2` as VERIFIED and the normal `0x30D7A` helper as asin-equivalent HIGH, while keeping complete caller-level XYZ->heading->pan semantics on HOLD. Do not modulo-normalize raw 0/360 endpoints before the downstream relative-angle branch is symbolically closed and parity-tested. This supersedes the v61 caller-level closure without discarding its retained instruction-level discoveries.

## ADR-015 — Git stores reproducible source, not commercial-derived payloads
**Status:** Accepted — 2026-09-18

Original commercial payloads, decoded Classic textures, exported room meshes, original audio and oversized deterministic forensic indexes are not part of normal Git history. They remain in integrity-checked snapshots/off-site backups. Git stores generators, validators, compact evidence and SHA-256 fingerprints sufficient to identify the excluded corpus.

## ADR-016 — v106 WORLD runtime serialization redirects the PUZZLES investigation
**Status:** Accepted — 2026-09-18

After v103-v105 exclude the audited direct-open paths and v106 verifies a structured WORLD.DAT runtime loader, the primary next experiment is WORLD writer/caller provenance. Do not infer that PUZZLES is unused or compiled into WORLD until a producer edge is independently demonstrated.


## ADR-023 — Candidate diagnostics must be observational
**Status:** ACCEPTED — 2026-09-18

The KG-001 Candidate 1 diagnostic layer may observe and record runtime state, visualize existing authored trigger bounds, and fail fast on missing required resources, but it must not directly set gameplay flags, puzzle nodes or inventory. Existing F8 audio debug and F9 parity capture are preserved; v116 reserves F6 for trigger visualization, F7 for the Candidate HUD and F10 for canonical state dumps. Diagnostic source-contract PASS does not promote any KG-001 runtime gate or forensic HOLD.


## ADR-024 — External localization packs and stable semantic IDs
**Status:** ACCEPTED — 2026-09-19

OpenAzrael localization is an external presentation-data layer over stable semantic string IDs. Runtime/gameplay code must not use editable English sentences as localization keys. Translator-facing canonical sources use POT/PO, English ships as the mandatory fallback, and distributable community/local language packs use versioned external PCK packages. External packs are mounted with core-resource replacement disabled and are restricted to a validated localization namespace. The architecture is defined in `docs/LOCALIZATION_ARCHITECTURE.md`. Runtime implementation is deliberately deferred until after the first clean KG-001 Candidate 2 runtime/manual cycle.

## ADR-025 — Candidate bug reporting is source-safe and observational

**Status:** accepted — 2026-09-19

- GitHub Issues is the canonical human bug tracker for OpenAzrael.
- F11 captures a diagnostic ZIP from KG-001 Candidate 2 without invoking gameplay mutators.
- Existing F6/F7/F8/F9/F10 meanings remain unchanged.
- Stable diagnostic IDs preserve authored/source names: ROOM, TRG, PUZ, FLAG and ITEM namespaces.
- Captures may contain screenshot, canonical state, bounded telemetry tail and system metadata, but never excluded commercial room/audio/texture payloads.
- Every reproducible fixed bug should gain regression evidence at the lowest useful automated layer.
- Critical bugs and reproducible softlocks continue to block `demo-known-good-001`.


## ADR-026 — KG-001 audio acceptance includes physical readiness

**Status:** ACCEPTED — 2026-09-19

G06 is no longer satisfied by the logical golden event stream alone. KG-001 requires an additional asset-backed Godot readiness regression proving that required Event/ambient WAV resources load, the Master bus is routable, recovered ambient emitters instantiate and report active playback, and a real Event-IR sound action creates a physical AudioStreamPlayer. Human audibility is accepted only in G10, while original Miles pan/volume parity remains a separate forensic HOLD.


## ADR-027 — Legacy # texture color-key is selected from the audited source palette

**Status:** ACCEPTED — 2026-09-20

A real audit of the 86-texture ATDEMO corpus supersedes the broader quantized-magenta uniqueness rule. Every one of the ten `#` textures has exactly one *used* raw source-palette sentinel with R=255, B=255 and G<=8, and no non-`#` texture uses that sentinel. `BLOOS4#.AZF` additionally contains a one-pixel near-magenta entry at palette index 9 (raw 248,0,255), while the actual key is index 5 (255,0,255); therefore broad post-quantization thresholding must not select transparency. Only pixels carrying the exact selected source-palette index receive alpha 0. XAF->GLB preserves the result as MASK. Complete original renderer transparency/blending semantics remain HOLD.

## ADR-028 — Candidate 2 source freezes before the second graphical run

**Status:** ACCEPTED — 2026-09-20

After the Issue #6 collision regression was widened to the canonical R1/R7/R8 entry views and Issue #11 was tightened to exact indexed-palette color-key selection, KG-001 Candidate 2 is source-frozen at `v116-context-v32`. No feature work, localization runtime, Generic Runtime refactor, remaster integration or unrelated forensic change may enter the Candidate branch before the complete fresh-checkout runtime suite and the short human blocker smoke test execute. Only fixes for failures discovered by that evidence may break the freeze.


## ADR-029 — Empirical corpus evidence may break a source freeze

**Status:** ACCEPTED — 2026-09-20

The v31 Candidate 2 freeze was deliberately broken by new empirical evidence from the actual ATDEMO 86-AZF corpus: `BLOOS4#.AZF` disproved the assumption that every `#` texture has exactly one used entry in the broad quantized-magenta range. The fix narrowed key selection to the raw source-palette sentinel family and added a hash-bound corpus audit. Candidate 2 is re-frozen at `v116-context-v32`. This is an allowed evidence-driven correction under ADR-028, not feature expansion.


## ADR-030 — Candidate 3 supersedes Candidate 2 as the active KG-001 evidence target

**Status:** ACCEPTED — 2026-09-21

Candidate 2 Windows automation remains immutable historical evidence, but its later manual traversal failure and subsequent source changes make it stale for promotion. KG-001 Candidate 3 is the active integration target. This supersedes only the scheduling/current-target language in ADR-024/ADR-028/ADR-029; it does not rewrite their historical decisions. Candidate 3 may not inherit Candidate 2 runtime PASS claims. It requires source CI and asset-backed v109/v110/v111/audio-v116/physical-v117/well-tongs-v118 PASS at the exact build SHA, then guarded export and G10.

Candidate 3 export provenance is fail-closed: the preflight receipt binds exact Git HEAD, Godot version, evidence hashes, the exact runtime asset path set and per-asset hashes. Any runtime asset mutation, addition or removal invalidates export. A PASS export receipt additionally requires exported-EXE startup smoke.

The manual upside-down R1 keyhole observation is fixed through a narrowly-scoped `KEYHOLE#` V-orientation compatibility correction with TONG6/MINETON# as a negative control. This correction is OpenAzrael presentation compatibility evidence, not recovery of a global original-renderer UV rule; final orientation remains a G10 visual check.

## ADR-031 — Candidate 3 requires PPPV v2 as a release oracle

Candidate 3 remains the authoritative runtime tree for KG-001 traversal, collision, audio, transparency, well+tongs and export hardening. Remaster Framework / PPPV v2 is layered on top as a mandatory validation oracle rather than replacing Candidate 3 runtime code. Exact-head preflight must require the current-bundle PPPV scenario suite plus integrity, a guarded chained playthrough, repeated deterministic semantic replay and determinism integrity. G04/G05/G08/G09 cannot pass from legacy v110/v111/v117/v118/v119/v120 evidence alone. Any required broken room transition is critical and blocks KG-001.

## ADR-032 — Separate project versions from internal evidence revisions

Project versions use the approved pre-1.0 semantic form `0.MAJOR.MINOR-dev`, `0.MAJOR.MINOR-rc.N`, and `0.MAJOR.MINOR`. KG-001 Candidate numbers are integration labels, while `v109`…`v120` and historical `v116-context-v32` are internal test/context/evidence revisions only. `demo-known-good-001` remains a separate immutable acceptance checkpoint. The exact Git SHA and receipts are authoritative build identity. See `docs/VERSIONING.md`.


## ADR-033 — Runtime room geometry is source-exact and complete

**Status:** ACCEPTED — 2026-09-22

Every playable OpenAzrael room must be derived from the original game/demo room geometry and imported completely. Partial room imports, hand-built approximations, AI-generated architecture, procedural substitutes, placeholder runtime meshes, or geometry invented to fill missing source data are forbidden. Missing source geometry is fail-closed and blocks the room/build rather than degrading to an approximation.

Engine-compatibility corrections may repair materials, alpha handling, triangle winding, normals, collision generation or reversible coordinate conversion, but must not change the authored room shape. State-dependent rooms require each original authored geometry state independently.

A geometry mismatch is a **critical build defect** and blocks Candidate export, KG promotion and release. The demo slice is guarded by geometry-render-parity v122; the same invariant applies to all future retail rooms. Schematic topology placeholders are permitted only in documentation and must never enter runtime assets.

See `docs/SOURCE_GEOMETRY_FIDELITY.md` and `data/source_geometry_policy.json`.
