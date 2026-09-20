# Validation Lab / PPPV

Status: reusable contract/evaluation POC implemented on
`tooling/remaster-framework-poc-01`.

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

## Player action modes

Current reusable modes:

- `input`: gameplay input actions such as move_forward/move_back;
- `interaction_probe`: the production interaction targeting/probe path;
- `physics_wait`: physics-frame waiting without logical shortcut.

Movement and look actions are invalid if declared through a non-input mode.
Interactions are invalid if declared through a direct input/logical shortcut
instead of the interaction-probe mode.

Setup state is kept separate from player actions. This permits isolated puzzle
tests to establish a known inventory precondition without pretending that setup
itself is part of the physical playthrough. Full-demo/retail playthroughs should
acquire those items through earlier real-player scenarios.

## Runtime evidence vocabulary

The framework currently recognizes arbitrary event kinds, with these conventions
used by OpenAzrael adapters:

- `player_action`: action_id + execution_mode;
- `movement`: real horizontal/goal progress result;
- `collision_support`: floor/support continuity and fall-through result;
- `stair_traversal`: real imported stair ascent/descent result;
- `interaction_probe`: target reachability/selection;
- `interaction`: accepted/rejected interaction outcome;
- `trigger`: trigger activation evidence;
- `demo_action_step`: ordered source-backed gameplay action step;
- `audio`: logical/runtime audio event;
- `animation`: animation or movement effect evidence;
- additional event kinds may be added by game-specific adapters.

Every event has a unique event_id, physics/render frame, kind, optional room, and
structured payload.

## Exact sequences

`EvidenceSequence` verifies ordered evidence streams.

For Well+Tongs, the positive scenario is generated from the recovered demo
contract and requires:

1. remove_room:R7Key
2. play_sound:979TONGS.WAV
3. add_room:R7Key
4. remove_room:RustyTongR6
5. remove_inventory:TONG6
6. default_take:R7Key

The current demo evidence states that the compiled action group has no transform
or rotation opcode, so the generated PPPV scenario explicitly forbids an
`invented_transform_tween` animation event. The framework therefore tests
faithfulness rather than adding an animation simply because an animation would
look plausible.

## State hashing

Logical before/after state is canonicalized deterministically and hashed with
SHA-256.

The evaluator report contains:

- PASS/FAIL;
- validation errors;
- evidence event count;
- before-state SHA-256;
- after-state SHA-256.

This is intended to become a stable regression oracle for CI and saved
playthrough evidence.

## OpenAzrael adapters

### Physical traversal v117

The adapter translates the existing physical traversal contract into:

- R1 forward/back real-input floor traversal;
- R8 step011 ascent/descent;
- R8 stairs__STAIR2 ascent/descent.

Generated scenarios require real gameplay input, collision support evidence,
movement progress, imported geometry, real landing probes, and no fake stair
fixture.

### Well+Tongs v118

The adapter generates two scenarios.

Positive:
- physical approach using gameplay movement input;
- target acquired through interaction probe;
- trigger activation;
- 979TONGS.WAV event;
- exact recovered demo action order;
- rusty_tongs consumed;
- well_key acquired;
- R7KeyTake and R7key transitions;
- no invented transform tween.

Negative:
- same physical approach and real interaction path;
- no rusty_tongs precondition;
- interaction rejection evidence;
- no demo action steps;
- no 979TONGS.WAV;
- no puzzle-state change.

The existing v118 runner currently proves the action stream by calling the
interaction node directly. That runner remains valuable source/runtime evidence,
but it is not yet the final PPPV implementation because the new contract requires
physical approach plus interaction-probe evidence.

## CLI

Adapt existing OpenAzrael contracts:

    python -m tools.openazrael_adapters.pppv \
      --physical-contract data/tests/kg001_physical_traversal_contract_v117.json \
      --well-contract data/tests/kg001_well_tongs_animation_contract_v118.json \
      --output pppv_scenarios.json

Evaluate one reusable scenario:

    python -m tools.remaster_framework.evaluate_validation \
      --scenario scenario.json \
      --evidence evidence.json \
      --before-state before.json \
      --after-state after.json \
      --output evaluation.json

## Next integration step

The next runtime-facing work is an evidence bus/driver for Godot that emits this
generic vocabulary while exercising the existing production Player,
InteractionProbe, collision geometry, triggers, audio and state code.

That integration should be done on top of the current physical-traversal/runtime
work, not by replacing it with a Python simulation.
