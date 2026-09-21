# Validation Lab / PPPV

Status: the reusable PPPV authoring/runtime framework is implemented on
`tooling/remaster-framework-poc-01`. The current KG-001 demo route is
**authoring-complete**, but the chained runtime playthrough is still
`NOT_EXECUTED`.

PPPV means Physical Player Puzzle Validation. A puzzle is not considered proven
merely because its function can be called or because a final flag has the
expected value. Validation must follow the same movement, targeting,
interaction, trigger, observable-effect, and state paths used by a real player.

## Current KG-001 status

The default OpenAzrael bundle currently materializes **20 reusable PPPV
scenarios** covering:

- R1 TONG6 pickup;
- R1 Door 1;
- R1 Door 2 positive and negative-without-key paths;
- physical R1 -> R7, R7 -> R1, R1 -> R8, and R8 -> R1 transition crossings;
- R7 Well+Tongs positive and negative-without-tongs paths;
- R7 water switchboard positive and wrong-sequence negative paths;
- R8 lens pickup and submerged-lens negative path;
- R8 lens placement;
- R8 zxplate-gated optical/secret-door sequence;
- R8 shield completion;
- R1 physical floor traversal;
- both audited R8 stair traversals.

The reference graph currently exposes six gameplay-graph targets and the
authored scenarios cover all six:

- `R7_WELL_TONGS_USE`;
- `R7_WATER_SWITCHBOARD_SOLVED`;
- `R8_LENS_PLACE`;
- `R8_OPTICAL_START`;
- `R8_SECRET_DOOR_OPEN`;
- `R8_TAKE_SHIELD`.

Therefore scenario/graph coverage is authoring-complete. This does **not** mean
the full physical playthrough has passed runtime validation.

## Synthetic-player v2 runtime guard

The guarded runtime path treats the synthetic test as a robot player rather
than a shortcut into game state. Every shared gameplay action now emits:

- a complete world-state snapshot before and after the action;
- frame-level avatar position, rotation, velocity and floor-support trajectory
  while physics-driven movement is active;
- a deterministic replay command/result record;
- hard failures for excessive per-frame vertical drops, sustained unsupported
  falling, or excessive vertical displacement during one action;
- a softlock watchdog event when canonical navigation makes no progress;
- destination room, spawn-position and facing validation after every room
  transition.

The guard is observational only. It must never write player transforms,
velocity, call `move_and_slide()`, call an interaction target directly, or
teleport during a gameplay action.

Transition coverage is source-complete rather than route-complete: the adapter
must contain one scenario for every row in `data/xaf_trigger_evidence.json`
`demo_transitions`. Missing either direction of an authored reciprocal
transition is a test failure, even if the shortest demo-completion route would
not use that direction.

## Core runtime rule

A passing scenario must provide evidence for the relevant subset of:

1. player action through an approved execution mode;
2. physical/interaction reachability;
3. trigger or interaction dispatch;
4. source-backed logical effects;
5. source-backed audio;
6. ordered effects when original order is known;
7. expected before/after logical state;
8. observable scene transform/visibility effects where gameplay visibly moves
   something;
9. absence of explicitly forbidden or invented behavior.

During gameplay actions the framework forbids teleporting the player, writing
horizontal velocity directly, calling `move_and_slide()` itself, or calling a
target's `interact()` directly.

## Reusable runtime components

- `PPPVEvidenceBus` — frame-indexed evidence with stable event IDs;
- `PPPVPlayerDriver` — production movement/look/interact input dispatch plus
  evidence-aware physics waits;
- `PPPVNavigator` — input-only steering to interactables/world points and
  mouse-input aiming without direct transform writes;
- `PPPVActionExecutor` — one action implementation shared by isolated and
  chained runners;
- `OpenAzraelPPPVObserver` — DemoState, LegacyEvents and CandidateDiagnostics
  translation into generic evidence;
- `PPPVSceneObserver` — read-only transform/visibility before/after evidence;
- `pppv_scenario_runner.gd` — isolated scenario execution;
- `pppv_playthrough_runner.gd` — continuous full-demo execution in one scene
  and one world state;
- `evaluate_validation.py` — deterministic isolated-scenario evaluator;
- `evaluate_playthrough.py` — deterministic chained-playthrough evaluator.

## Player action modes

- `input` — normal movement or mouse-look input;
- `interaction_probe` — the production InteractionProbe path;
- `physics_wait` — bounded physics-frame waiting without a gameplay shortcut.

Scenario setup is allowed only before an isolated scenario. In the chained
full-demo runner, setup dictionaries are **checked as preconditions rather than
applied**, so an item required later in the route must actually have been
acquired by an earlier player action.

## Evidence vocabulary

The generic evidence stream currently includes:

- `player_action`;
- `movement` / `movement_sample`;
- `collision_support`;
- `stair_traversal`;
- `interaction_probe`;
- `trigger`;
- `room_transition`;
- `demo_action_step`;
- `audio`;
- `state_change`;
- `scene_change`;
- `aim`;
- `physics_wait`;
- `save_load_checkpoint`;
- `navigation_failure`.

OpenAzrael reuses the existing `CandidateDiagnostics.event_recorded` channel
for interaction dispatch, trigger enter/exit and room-transition evidence rather
than introducing a parallel production trigger system.

## Well+Tongs evidence boundary

The positive v118-derived scenario requires the recovered action order:

1. `remove_room:R7Key`
2. `play_sound:979TONGS.WAV`
3. `add_room:R7Key`
4. `remove_room:RustyTongR6`
5. `remove_inventory:TONG6`
6. `default_take:R7Key`

The recovered action stream contains no transform/rotation opcode, so an
`invented_transform_tween` is explicitly forbidden.

## R8 optical evidence boundary

The optical scenario requires a real player to:

1. physically enter the authored `zxplate` trigger;
2. remain there while aiming the production InteractionProbe at
   `Interact_R8Bible`;
3. dispatch the normal interact input;
4. wait a bounded physics interval for the asynchronous sequence.

PASS requires:

- `R8LensLook` and `R8RaiseTimer` state changes;
- `S121.WAV`;
- `DoorR8` state change;
- `799SECDR.WAV`;
- lens transform movement;
- secret-door rotation;
- shield visibility transition.

The unresolved `R8Counter` opcode semantics and reconstructed interpolation
timings remain explicitly **non-gating reconstruction**.

## Full-demo chained orchestration

The real-player plan is:

`R1 -> R7 -> R1 -> R8`

All required scenario and transition segments are now authored, so the plan
reports `READY` with no authoring-blocked steps.

`READY` means **ready to execute**, not runtime-validated.

The chained runner:

- loads `main.tscn` once;
- resets DemoState once at the beginning;
- carries one continuous world state across all puzzle/transition segments;
- checks isolated scenario setup values as preconditions rather than injecting
  them;
- executes every gameplay action through `PPPVActionExecutor`;
- performs explicit canonical-state save/restore roundtrips at planned
  checkpoints;
- requires the final canonical state SHA-256 to match the established KG-001
  success hash.

The checkpoint implementation is a canonical DemoState roundtrip. It must not be
described as proof of a future disk-save UI/system.

The historical v111 full-demo runner remains useful as a legacy interaction,
audio and final-hash regression oracle, but is not accepted as physical-player
evidence because it directly calls interaction methods and places the player on
trigger centroids.

## Plan/runtime identity

Every playthrough plan has a deterministic `plan_sha256`.

Candidate release tooling always writes and hashes
`pppv_playthrough_plan.json`. If a
`kg001_pppv_playthrough.json` runtime bundle exists, its embedded
`plan_sha256` must exactly match the current candidate plan before the runtime
or evaluation can enter build provenance. This prevents a PASS from an older
plan being attached to a newer candidate.

The guarded playthrough is now required evidence for G08, and candidate-bound
suite/determinism integrity is required for G09. A successful chained
playthrough is executed at least twice; both evaluations must share the same
semantic replay fingerprint and final canonical state hash.

## F11 diagnostics

Source-safe candidate metadata can be staged into `data/runtime/`.
F11 bug-report capture can include, when present and schema-valid:

- build provenance;
- release-gate summary;
- PPPV coverage;
- chained PPPV playthrough evaluation.

Each included metadata file is SHA-256 bound in the bug-report manifest. Original
commercial room/audio/texture assets are not included.

## Commands

Build the candidate framework evidence bundle:

    python -m tools.openazrael_adapters.kg001_candidate_framework \
      --repo-root . \
      --evidence-root .tmp/kg001 \
      --commit-sha <40-char-git-sha> \
      --godot-version <version>

This writes the reusable scenario bundle and
`pppv_playthrough_plan.json` alongside release/provenance artifacts.

Run the chained physical playthrough once local runtime assets are available:

    godot --headless --path . \
      --script res://scripts/validation/pppv_playthrough_runner.gd \
      -- --pppv-plan=.tmp/kg001/pppv_playthrough_plan.json \
         --pppv-scenarios=.tmp/kg001/pppv_scenarios.json \
         --pppv-output=.tmp/kg001/kg001_pppv_playthrough.json

Evaluate the resulting bundle independently:

    python -m tools.remaster_framework.evaluate_playthrough \
      --runtime-bundle .tmp/kg001/kg001_pppv_playthrough.json \
      --output .tmp/kg001/kg001_pppv_playthrough_evaluation.json

Re-run the candidate framework command afterwards to bind the matching runtime
and evaluation hashes into build provenance.

## Remaining Validation Lab work

The remaining major gate is **execution**, not scenario authoring:

- run the chained full-demo PPPV twice against a fresh candidate with the local
  R1/R7/R8 assets;
- require matching semantic replay fingerprints and final state hashes;
- inspect any navigation/interaction failures and fix production/runtime issues
  rather than adding shortcuts;
- confirm the visual/audio evidence for the R8 optical sequence;
- confirm every canonical-state checkpoint and final hash;
- run the current-candidate exhaustive state-space and deterministic adversarial
  fuzz reports before G03 can pass.

GitHub-hosted Actions are currently infrastructure-blocked for this branch:
diagnostic jobs fail before even a `python3 --version` step executes. Recent red
runs therefore do not establish a source-code failure. Static registry checks on
the current tooling branch have found no duplicate tool IDs or missing
entrypoints; local/runtime execution remains the required next validation step.

The shared interfaces are intentionally game-independent so the same validation
framework can later be reused by OpenCadaver.
