# OpenAzrael KG-001 — Known-Good Demo Acceptance Plan

**Status:** ACCEPTED
**Target tag:** `demo-known-good-001`
**Scope:** demo integration slice `R1 -> R7 -> R8`
**Runtime:** Godot 4

KG-001 is the first reproducible "known-good" OpenAzrael demo baseline. It is a release/quality gate, not a claim that every original Azrael's Tear runtime semantic has been recovered.

## Release rule

The tag `demo-known-good-001` may be created only when all required gates are PASS and the final defect condition is simultaneously true:

- zero known critical bugs;
- zero reproducible softlocks;
- zero failed required gates;
- fresh-checkout verification passes;
- final manual sanity check is completed by the user.

A forensic HOLD may remain only when it is explicitly documented, does not invalidate the exercised demo behavior, and is not silently promoted to VERIFIED.

## Required gates

### G00 — Context and evidence integrity
Validate canonical context, checkpoint consistency, repository safety rules, evidence lifecycle labels and required artifacts. The source-safe Git checkout must not contain excluded original/commercial payloads.

### G01 — Data validation
Validate all demo data/IR inputs used by the runtime. Parsers must reject malformed/truncated input deterministically and must not reinterpret UNKNOWN fields as recovered semantics.

### G02 — Unit / gameplay logic
Exercise deterministic gameplay-state primitives and Event IR operations independently. Every supported operation must have positive, negative and idempotency/repeat-behavior coverage where applicable.

### G03 — Puzzle state-space exploration
Enumerate every reachable state for the demo puzzle subset and all supported actions from each state. Detect dead states, unintended cycles, unreachable required states and softlocks. The expected successful path must remain reachable from every intended precondition state.

### G04 — Room, transition and physical traversal state
Verify R1/R7/R8 room entry/exit, transition preconditions and preservation of persistent state across transitions. Re-entering a room must not accidentally reset one-shot or solved state unless explicitly specified.

This gate also requires asset-backed physical traversal through the production `CharacterBody3D` path. The automated suite must drive the real gameplay input actions over the canonical R1 starting floor and prove that the player does not fall through while moving. It must also traverse both imported R8 tread sequences (`step011__mesh` and the main `stairs__STAIR2`) upward and downward using the real player capsule, collision layers/masks, gravity and `player.gd`; a raycast-only floor check, stationary settle, synthetic proxy staircase, or teleport-to-result is not sufficient evidence.

### G05 — Trigger semantics
Exercise every demo trigger/event edge with valid and invalid preconditions, repeated activation, ordering and boundary cases. No trigger may fire twice when modeled as one-shot, disappear when persistent, or leave the state machine in an undefined state.

### G06 — Logical audio plus physical playback readiness
First run gameplay with the deterministic capture/mock path and compare emitted logical events against the accepted golden stream. Then run the asset-backed physical-audio readiness regression: required Event/ambient WAVs must exist and load as AudioStreams, the Master bus must exist and be unmuted/not effectively silent, recovered ambient emitters must instantiate as R1=2 / R7=3 / R8=2 with valid streams and `playing=true`, and a real Event-IR `play_sound` action must create a playing `AudioStreamPlayer`.

This automated layer proves runtime readiness, not human audibility and not original Miles pan/volume fidelity. Human audibility remains part of G10; original-runtime pan/volume parity remains a separate forensic oracle.

### G07 — Save/load state hash
At defined checkpoints serialize state, reload it and compare a canonical state hash plus explicit invariants. Save/load must preserve solved puzzles, inventory, room/transition state, trigger one-shots and active logical audio state where persistence is defined.

### G08 — Headless synthetic full-demo playthrough
Run a deterministic, no-human-input playthrough from clean state through the full R1->R7->R8 demo route. Exercise required interactions, transitions and puzzle completion. The run must terminate in the expected success state with no assertion, uncaught error, dead end or softlock.

### G09 — Fresh-checkout build verification
From a clean checkout of the candidate commit, restore only permitted/reproducible dependencies and local excluded assets through the documented workflow, then run source/context checks plus the automated KG-001 suite. No untracked local source edit may be required.

### G10 — Manual sanity check
After all automated gates pass, perform a short human run of the candidate build. Confirm launch, controls, room traversal, key interactions, puzzle completion, save/load behavior, that expected ambient/event audio is actually audible at usable levels, and that legacy cutout textures render with their intended binary mask rather than visible magenta key color. A logical event or a runtime player reporting `playing=true` is not a substitute for the listening check; source-level alpha metadata is likewise not a substitute for the graphical transparency check. Record any discrepancy before tagging.

## Evidence to archive

For the candidate commit record: Git commit SHA, Godot version, source-data fingerprints, decoder/importer versions, test command versions, gate results, synthetic-playthrough trace/state hashes, fresh-checkout result, manual sanity result, known non-critical limitations and checksums for the retained milestone snapshot.

## Failure policy

Any critical bug, reproducible softlock, required-gate failure, or explicitly recorded KG-001 release blocker blocks KG-001. A failure is fixed first, then the affected gate and all dependent gates are rerun. The tag is immutable evidence of the passing candidate; later fixes create a new known-good tag rather than rewriting KG-001.
