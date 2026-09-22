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

The exhaustive graph is complemented by deterministic adversarial state fuzzing. Seeded random walks deliberately repeat actions, issue actions under invalid preconditions, restart from the initial state, and verify transition determinism, no-op purity, logical invariants, monotonic progress facts, membership in the exhaustive reachable graph, and continued reachability of a success state. Both reports must be generated for the current candidate; a previously committed state-space PASS is not sufficient.

### G04 — Room and transition state
Verify R1/R7/R8 room entry/exit, transition preconditions and preservation of persistent state across transitions. Re-entering a room must not accidentally reset one-shot or solved state unless explicitly specified.

G04 requires both the legacy transition-state oracle and the current-bundle PPPV scenario suite plus its integrity report. Every authored demo transition must be crossed by the production avatar through normal gameplay input, must emit the expected trigger/room-transition evidence within the crossing action's causal event window, and must land at the expected destination spawn and facing. Transition scenarios are never allowed to fall back to the legacy v117 bridge. A missing, broken, incorrect, one-way-when-reciprocal, or softlocking required room transition is a **critical bug** and blocks KG-001.

### G05 — Trigger semantics
Exercise every demo trigger/event edge with valid and invalid preconditions, repeated activation, ordering and boundary cases. No trigger may fire twice when modeled as one-shot, disappear when persistent, or leave the state machine in an undefined state. Required evidence is action-scoped: a correct final state is insufficient when the matching trigger/audio/state effect occurred during the wrong player action.

### G06 — Audio event stream
Run gameplay with a deterministic mock audio backend and compare emitted logical events against golden streams: sound identity, start/stop/loop intent, emitter/reference id and event ordering. This gate does not claim original-runtime pan/volume parity; that remains a separate forensic oracle.

### G07 — Save/load state hash
At defined checkpoints serialize state, reload it and compare a canonical state hash plus explicit invariants. Save/load must preserve solved puzzles, inventory, room/transition state, trigger one-shots and active logical audio state where persistence is defined.

### G08 — Headless synthetic full-demo playthrough
Run a deterministic, no-human-input playthrough from clean state through the full R1->R7->R8 demo route. Exercise required interactions, transitions and puzzle completion. The run must terminate in the expected success state with no assertion, uncaught error, dead end or softlock.

The final G08 oracle is the guarded chained PPPV runtime: actions are executed through production input paths, movement is sampled at physics-frame granularity, world state is snapshotted before/after each action, navigation has a softlock watchdog, and every action is retained in deterministic replay evidence. The complete playthrough must pass at least twice. Both runs must independently evaluate to PASS, finish with the same canonical state hash, and produce the same semantic replay fingerprint; absolute physics-frame timing is intentionally excluded from that fingerprint. The determinism summary is itself checked against the current playthrough plan, scenario bundle, and both evaluation artifacts. The legacy v111 playthrough remains a required compatibility oracle but is no longer sufficient by itself.

### G09 — Fresh-checkout build verification
From a clean checkout of the candidate commit, restore only permitted/reproducible dependencies and local excluded assets through the documented workflow, then run source/context checks plus the automated KG-001 suite. No untracked local source edit may be required. G09 also requires the PPPV suite-integrity and determinism-integrity reports to PASS so a stale green artifact from an earlier scenario bundle or playthrough plan cannot satisfy the gate.

### G10 — Manual sanity check
After all automated gates pass, perform a short human run of the candidate build. Confirm launch, controls, room traversal, key interactions, puzzle completion, expected logical audio and save/load behavior. Record any discrepancy before tagging.

## Evidence to archive

For the candidate commit record: Git commit SHA, Godot version, source-data fingerprints, decoder/importer versions, test command versions, gate results, per-scenario execution profile, synthetic-playthrough replay/state hashes, semantic replay fingerprints from repeated runs, suite/determinism integrity reports, failure reproducer when applicable, fresh-checkout result, manual sanity result, known non-critical limitations and checksums for the retained milestone snapshot.

## Failure policy

Any critical bug, reproducible softlock or required-gate failure blocks KG-001. In particular, any unresolved required room-to-room transition is classified as critical. A failure is fixed first, then the affected gate and all dependent gates are rerun. The tag is immutable evidence of the passing candidate; later fixes create a new known-good tag rather than rewriting KG-001.
