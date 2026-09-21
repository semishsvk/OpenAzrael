# Validation Lab / PPPV

Status: reusable contract, planning, Godot driver, evidence, and evaluation POC
implemented on `tooling/remaster-framework-poc-01`.

PPPV means Physical Player Puzzle Validation. Its purpose is to prove that a
puzzle can be solved through the same movement, targeting, interaction, trigger,
audio/visual, and state paths used by a real player.

## Core rule

A puzzle test does not pass merely because a gameplay function can be called or
because the final flag has the expected value.

A passing scenario must provide evidence for:

1. player action through an approved execution mode;
2. physical/interaction reachability when relevant;
3. trigger or interaction activation;
4. observable effects required by source evidence;
5. exact ordered effects when original action order is known;
6. expected logical state transition;
7. absence of explicitly forbidden invented behavior.

Test setup is separate from gameplay actions. Setup may load a room, select an
evidence-backed spawn view, or establish a required inventory precondition.
After action execution starts, movement must use production player input and
interactions must use the production InteractionProbe path.

## Implemented reusable runtime components

- `PPVPEvidenceBus`: frame-indexed runtime evidence with stable event IDs;
- `PPPVPlayerDriver`: real gameplay movement/look/interact input dispatch;
- `PPPVNavigator`: mouse-input steering + move_forward toward interaction targets;
- `OpenAzraelPPPVObserver`: state/audio/action/diagnostic evidence translation;
- `pppv_scenario_runner.gd`: scenario setup, action execution, evidence capture,
  and before/after state snapshots;
- Python runtime-bundle evaluator producing deterministic PASS/FAIL reports.

The navigator never sets the player's position, rotation, velocity, or calls
`move_and_slide()`. If the target cannot be found, becomes unreachable, or
movement stalls, it records a navigation failure instead of teleporting.

The Player Driver never calls a target's `interact()` directly. It dispatches
the production `interact` input event after the production InteractionProbe has
identified the expected target.

## Existing OpenAzrael evidence reused

The framework does not add a new production trigger system merely for tests.
`CandidateDiagnostics.event_recorded` already exposes:

- interaction dispatch;
- trigger enter/exit;
- room transitions.

The PPPV observer translates those existing diagnostics into the generic
`trigger` / `room_transition` evidence vocabulary. DemoState signals provide
inventory/flag/puzzle changes and LegacyEvents provides logical audio evidence.

## Player action modes

Current reusable modes:

- `input`: gameplay input actions such as move_forward/move_back;
- `interaction_probe`: production interaction targeting/probe path;
- `physics_wait`: physics-frame waiting without a logical shortcut.

Movement and look actions are invalid through a non-input mode. Interactions are
invalid through a direct logical call instead of the interaction-probe mode.

## Runtime evidence vocabulary

OpenAzrael currently emits or can translate:

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
- `animation`;
- `navigation_failure`.

Every evidence event has a unique event_id, physics frame, kind, optional room,
and structured payload.

## Runtime capability preflight

`tools/openazrael_adapters/runtime_capabilities.py` checks whether a source tree
has the hooks required by the generic PPPV runtime.

The current tooling branch is expected to report:

- generic PPPV runtime core: READY;
- exact Well+Tongs v118 evidence: READY.

The v117/v118 runtime changes were integrated deliberately as a minimal parity
set rather than by merging the highly diverged physical-traversal branch. CI
requires both the generic PPPV core and the v117/v118 source contracts to remain
valid.

## Coverage and planning

`PPPV Coverage Audit` compares the deterministic reference graph with the
scenario bundle. Every gameplay graph must eventually have at least one declared
PPPV scenario.

`PPPV Scenario Planner` turns the reference graph into a puzzle-by-puzzle
authoring backlog containing:

- owning room;
- source evidence;
- expected state effects;
- expected audio effects;
- other referenced assets;
- scenario coverage status.

The current integrated IR contains six gameplay targets, including the verified
`R7_WELL_TONGS_USE` graph. The candidate framework automatically materializes
five reusable PPPV scenarios from the v117/v118 contracts: three physical
traversal scenarios plus positive and negative Well+Tongs scenarios. Other
gameplay targets remain visible as uncovered authoring work rather than being
silently omitted.

This mechanism is intended to scale to the full retail build: newly recovered
puzzles automatically appear as uncovered targets rather than being silently
omitted from the test suite.

## Exact sequences: Well+Tongs

The positive scenario generated from the v118 contract requires:

1. remove_room:R7Key
2. play_sound:979TONGS.WAV
3. add_room:R7Key
4. remove_room:RustyTongR6
5. remove_inventory:TONG6
6. default_take:R7Key

The recovered demo action group has no transform or rotation opcode. The PPPV
scenario therefore explicitly forbids an `invented_transform_tween` event.

Positive path additionally requires real physical approach, InteractionProbe
selection, interaction dispatch, 979TONGS audio, and the expected state changes.

Negative path uses the same real approach and interaction dispatch without
rusty_tongs, then proves that no demo action steps or 979TONGS audio occurred and
that the puzzle state did not change.

## State hashing

Logical before/after state is canonicalized deterministically and hashed with
SHA-256. The evaluator report includes:

- PASS/FAIL;
- validation errors;
- runtime execution status/failures;
- evidence event count;
- before-state SHA-256;
- after-state SHA-256.

## Commands

Adapt OpenAzrael contracts:

    python -m tools.openazrael_adapters.pppv \
      --physical-contract data/tests/kg001_physical_traversal_contract_v117.json \
      --well-contract data/tests/kg001_well_tongs_animation_contract_v118.json \
      --output pppv_scenarios.json

Audit runtime capabilities:

    python -m tools.openazrael_adapters.runtime_capabilities . --require-core

Build a coverage report:

    python -m tools.remaster_framework.coverage \
      --reference-graph reference_graph.json \
      --scenarios pppv_scenarios.json

Build a puzzle-by-puzzle authoring plan:

    python -m tools.remaster_framework.planning \
      --reference-graph reference_graph.json \
      --scenarios pppv_scenarios.json

Run one scenario in Godot:

    godot --headless --path . \
      --script res://scripts/validation/pppv_scenario_runner.gd \
      -- --pppv-scenario=scenario.json --pppv-output=runtime.json

Evaluate its complete runtime bundle:

    python -m tools.remaster_framework.evaluate_validation \
      --runtime-bundle runtime.json \
      --output evaluation.json

## Remaining Validation Lab integration

- bridge the proven v117 collision/support/stair measurements into the generic
  `collision_support` and `stair_traversal` evidence vocabulary, preserving
  the existing real-geometry assertions;
- migrate the legacy v118 direct-call runner onto the generic Navigator /
  InteractionProbe execution path for the final PPPV runtime oracle while
  keeping the current v118 runner as parity evidence;
- add full-demo orchestration where inventory must be acquired through earlier
  real-player scenarios rather than setup;
- add save/load continuity and room-transition chains to the full-demo runner;
- require complete PPPV gameplay coverage before a future retail Known-Good gate.

The reusable core must remain game-independent enough to be extracted later for
OpenCadaver rather than becoming an OpenAzrael-only test harness.
