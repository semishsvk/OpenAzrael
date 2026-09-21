# OpenAzrael v108 — KG-001 deterministic state-space harness

v108 adds the first executable source-safe KG-001 state/puzzle harness. It consumes the tracked v87 gameplay Event IR and tracked R1/R7/R8 trigger/transition IR, then exhaustively applies every supported demo action to every reachable logical state.

## Result
- **104 reachable states**
- **214 changed transition edges**
- **1560 action attempts**
- **1346 invalid/idempotent no-op attempts**
- **6 success states**
- **0 softlock states**
- **0 non-success dead-end states**
- shortest successful route: **15 actions**

Every reachable logical state can reach `demo_complete=true` under the modeled demo rules.

## Canonical state hash
`scripts/demo_state.gd` exposes `canonical_state_payload()`, `canonical_state_json()` and `canonical_state_hash()`. Dictionary keys are converted to sorted key/value pairs before JSON serialization. The persistent payload is `[schema, inventory, flags, puzzle_nodes, values]`.

Reference hashes:
- clean state: `90fdebf6dff29bf2b4b78980615205c2e6c067b65a28c2aff0b7f10b513f6abf`
- shortest-path completed state: `e266137c74746996608ffcdd165b6a1072e2c9f55833473546061ccac0e05902`

## Shortest synthetic route
`pickup_rusty_tongs -> open_r1_door1 -> R1/R7 -> retrieve_well_key -> lever -> wheel -> lever -> R7/R1 -> open_r1_door2 -> R1/R8 -> retrieve_r8_lens -> place_r8_lens -> start_optical_sequence -> finish_optical_sequence -> take_shield`

Logical Event IR sound stream:
`979TONGS.WAV -> S152V2.WAV -> S137.WAV -> S121.WAV -> 799SECDR.WAV`

Wrong switch inputs, repeats/idempotent actions, partial switch progress, room exits/re-entry and leaving R8 during its room-local optical sequence are included in the state search.

## Evidence boundary
This is a **source-model PASS**, not final KG-001 runtime PASS. It does not prove original timing/motion, Classic audio pan/volume parity, or the complete original PUZZLES/WORLD compiler. Existing confidence/HOLD labels remain unchanged. Final KG-001 still requires Godot headless/runtime, save/load, fresh-checkout and manual gates.
