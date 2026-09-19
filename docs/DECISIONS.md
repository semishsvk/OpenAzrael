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

## ADR-024 — Texture remaster layers are non-destructive generated presentation assets
**Status:** ACCEPTED — 2026-09-19

Classic decoded texture evidence remains immutable and separate from generated presentation layers. Texture Lab uses four explicit tiers: Classic, deterministic mathematical Enhanced, AI Restored and AI Recreated. Generated pixels never replace Classic source evidence and do not alter geometry, UVs, collision, gameplay or recovered identifiers. Commercial-derived Classic pixels and generated derivative pixels remain outside normal Git history; Git stores repository-safe tools, configuration, workflow metadata, tests and reviewed compact fingerprints/reports. AI fidelity metrics and visual candidates remain observational until explicit calibration/review promotes a production choice.
