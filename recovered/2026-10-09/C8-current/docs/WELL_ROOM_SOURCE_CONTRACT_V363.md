# OpenAzrael Candidate 8 — Well Room source-mechanism checkpoint v363

Status: `SOURCE_CONDITION_AND_ACTION_ORDER_PASS / GODOT_FIDELITY_HOLD`.

## Authority and coordinates

Authoritative, read-only inputs: ATDEMO `R.EXE` SHA-256
`381e4f5c61e4bb8c27f06b1944e6673bbebc39ca219cc08fb9f948da2ca37c00`
and `WORLD.DAT` SHA-256
`f055948e302fa2f6ba364f7ebd3b4bc45f20ef4445af4946c63e4e313a084ae9`.

The v312 corrected bound-LE reader is mandatory. Historic v115 object offsets were
computed using an incorrect image origin. The condition evaluator is now object-1
`0x2C3B4` (its direct CALL at `0x2C887`), **not** the old `0x2990C`.
The indirect condition jump table at `0x2C368` is verified against raw LE
relocations, including entries `0x04 → 0x2C50A` and `0x0A → 0x2C533`.

## Recovered source operands and motion

Both movement handlers extract the axis selector from action record byte `+9`:
`mov eax, [record+6]; sar eax,24`. This byte was historically mislabeled
"mode". For `0x17` rotation, selector 0→source Y, 1→source X,
2→source Z; for `0x18` translation, selector 0→source Z,
1→source Y, 2→source X. These are SOURCE ENGINE vector components,
not proven Godot/world coordinate or handedness parity. Rotation operands are
signed 16-bit degrees multiplied by original π/180 constants; translation
operands are 32-bit floats.

The 24 source movement records in R7 group 4 have inverse pairs. Counts 5,
10 and 15 are scheduler steps, **not verified wall-clock durations**.
Current experimental Godot executor performs source-component-local-space replay,
but full original composition, pivot handling, callback cadence and visual diff
remain HOLD. Production motion guard remains false.

## Verified conditional branch semantics

WORLD 37-byte condition opcode 4 checks `state_u16[index] != 0` using
array pointer `0x438A4`; condition opcode 10 checks `== 0`.
Group-4 node 8 contains complementary conditions on **index 44**, and node
16 contains complementary conditions on **index 46**. In both cases,
slot 0 is opcode 4 (nonzero) and slot 1 is opcode 10 (zero).
The mapping of numeric indices 44/46 to human-readable game flags and
the runtime origin of their values are still **unverified**.

`R7SwitchStep` is a reconstructed three-step Godot progression; it is not
an authoritative alias for source index 46. Do not release animations by
assuming step 0 → nonzero or step 2 → zero without original runtime replay.

## Complete Well Room interaction chains

The audited ten WORLD nodes (2,3,5,6,8,10,11,13,14,16) contain **12
condition groups and 48 ordered 27-byte actions**, not just 24 movement actions:

- 16 rotations (`0x17`)
- 8 translations (`0x18`)
- 12 source sound actions (`0x28`)
- 8 source state-array writes (opcode 0x04) and 4 opcode-0x01 action records whose full semantics remain HOLD

Sound stems are source-bound: `983TUNK` on nodes 2/3/10/11,
`977TURN` on 5/6/13/14, `982PUSH` on node 8/16 slot 0,
and `981PULL` on node 8/16 slot 1. Sound records indicate R7 room
context (1). The order of records in WORLD is verified, but their physical
playback timestamps and relative asynchronous trigger timings are not.

Crucially, node 16 slot 0 has five actions
`[0x18,0x17,0x04,0x01,0x28]` and slot 1 seven
`[0x18,0x17,0x04,0x01,0x04,0x04,0x28]`. Node 8 has analogous
opposite branches, with the sound record earlier in its action list.
The original opcode 0x04 action handler (object1 0x1B2B1) writes
state_u16[record+1] = record+3 through global state array 0x438A4.
It is the same array checked by the condition 0x04/0x0A dispatcher.
Node 16 slot 0 writes state 46=0; slot 1 writes state 46=1
and resets source states 42/43 to zero. Node 8 does the same for
state 44. The other four opcode 0x01 actions remain a separate,
partly decoded runtime path and are not treated as no-ops for
fidelity. Do not drop the extra state records when implementing gameplay.

## Deterministic regeneration and validation

From the canonical checkout with local ATDEMO available:

```text
python tools/build_well_source_actions_v358.py
python tools/build_well_condition_gates_v362.py
python tools/build_well_interaction_source_v363.py
python tools/run_well_source_gate_v347.py
godot --headless --path . --script res://scripts/kg001_r7_source_axis_replay_runner_v361.gd
godot --headless --path . --script res://scripts/kg001_r7_condition_branch_runner_v363.gd
```

Generated JSON remains in ignored `data/runtime_generated`; all source-safe
generators, tests and declarative axis contract are tracked. No source payload,
record bytes, proprietary movie frames, audio samples, model meshes or derived
commercial binaries are added to Git.

## Unclosed gates

1. Connect numeric source condition indices 44/46 to original runtime state,
   events, and `PUZZLES.DAT` semantics.
2. Determine all opaque `0x01`/`0x04` action semantics in these branches.
3. Validate axis/pivot/local-parent matrix composition against executed
   original instructions (not just static source data).
4. Verify original callback frequency, pause behavior, queue/flush and mid-step
   save/load semantics.
5. Validate audio trigger order *and physical timing* against original gameplay.
6. Re-run complete full-demo regression, original-vs-Godot replay/frame diffs,
   G10, and package release gates before claiming a final Candidate 8.

This checkpoint permits SOURCE contract PASS only. No fidelity, known-good,
Windows/macOS Candidate release or Retail promotion is authorized.

## v365 source-state interpreter (isolated)

The original-verified 101-word WORLD section-4 runtime state array is
initialized to zero by the original loader. A new source-only handler model
uses opcode-0x04 state writes and complementary 0x04/0x0A conditions,
preserving source action order and marking opcode 0x01 as an unresolved
callback. At initial zero source state, a node-16 activation selects slot
1 (sound 981PULL, then state 46=1). The next activation selects slot 0
(sound 982PUSH, then state 46=0). These findings are verified for the
*numeric source state model*, NOT for the reconstructed R7SwitchStep
trigger sequence: original initial gameplay initialization and source
action firing conditions need original-runtime observation.

The model deliberately does not render geometry or play sound, and it does
not write to production DemoState. Automated tests live in
tools/test_well_state_opcode_v365.py and
scripts/kg001_r7_source_state_runner_v365.gd; local source gate and C8
regression orchestrator include both. Original fidelity remains HOLD.

## v366 opcode 0x01 source callback guard

In the corrected bound LE image the opcode 0x01 dispatch target is
object-1 relative 0x1B222. It indexes the WORLD section-3 runtime
object table at global 0x438EC. For source record index 0, if object
field +0x0C is nonzero, it invokes 0x1A90C and then resets the field
to zero. The called routine scans a bounded ten-entry list of callback
identifiers at 0x24766 and invalidates its matched entry using 0xFFFF.
The original WORLD section-3 record count is three, and the four
Well Room opcode-0x01 records all reference section-3 record index 0.

This closes selected instruction/data flow for opcode 0x01 but NOT
its complete gameplay meaning: the trigger/callback identity,
initial activation conditions and fidelity-visible consequences are
still HOLD. The source IR keeps these as opaque state actions with
provenance fields; the isolated numeric state interpreter flags them
without inventing effects. Automated test:
tools/test_well_callback_opcode_v366.py.

## v367 save/load compatibility and invalid snapshot rejection

The isolated R7 transform bridge now serializes only its experimental
queue/executor state under DemoState values key
R7SourceTransformSnapshotV364. No key is created by passive R7 room load.
Production DemoState validates this nested payload *before* replacing
any live inventory, flags, puzzle nodes or values. The validator
refuses unsupported versions, missing fields, invalid opcode/axis/target
and progress counts, nonnumeric magnitudes and inconsistent applied
history. Legacy saves without the experimental key remain valid.

The guard does NOT imply the source game used this serialization format.
R7 persistence is an experimental Godot reconstruction pending direct
origin-vs-Godot save/load runtime parity. Regression test
scripts/kg001_r7_save_guard_runner_v367.gd exercises malformed save
payloads and verifies that rejected saves do not alter the existing
canonical state hash.

## v368 source-authored plaque sequence: PULL → TURN → PUSH

The canonical ATDEMO README.TXT SHA-256
`2976197be180e90d9370c580d5f07491c84d459d9f1e26ada58e993a1230adc2`
explicitly describes the well solution as right-most lever to *pull*
the right pipe out, lower-right wheel to rotate, then the lever to
*put it back*. This is independent of the engine code evidence.

The original source WORLD section-4 state array has 101 initially
zero entries; for node 16 source index 46=0 selects slot 1, which
contains `981PULL.WAV` and writes 46=1. The subsequent node 16
activation selects slot 0, which contains `982PUSH.WAV` and writes
46=0. The earlier C8 synthetic Godot order (PUSH first / PULL last)
was reversed and corrected in v368, including the source action
selector, activation guard, logical audio assertion and cursor.
`PUSH.PCX` is an original source artwork available in the existing
cursor manifest, but original per-step cursor semantics and physical
audio timing remain fidelity HOLD. Node-13 vs node-14 wheel direction
is still an isolated experimental selection, not original runtime
verified.

Regression: `tools/test_well_plaque_order_v368.py`, with full Godot
flow checked by `scripts/kg001_r7_plaque_flow_runner_v368.gd`.
