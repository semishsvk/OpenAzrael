# OpenAzrael Test Matrix

**Canonical checkpoint:** `v110-context-v18`

| Area | Current checkpoint | Status | Boundary |
|---|---:|---|---|
| Project context | v110-context-v18 | PASS target | Source/context validation |
| Graphics pipeline | v44 | PASS | Runtime screenshot parity separate |
| Demo coordinate transform | v67 | HIGH | Retail-global still pending |
| Classic audio reference/capture pipeline | v58-v86 | TESTED/HIGH pieces | Genuine original parity UNOBSERVED |
| Gameplay Event IR | v87-v89 | Implemented/Tested | Not all source semantics exact |
| PUZZLES structural grammar | v90-v100 | HIGH structural subsets | Full enclosing grammar HOLD |
| Direct PUZZLES open audit | v103-v105 | HIGH for audited mechanisms | Indirect/custom paths not excluded |
| WORLD.DAT runtime loader | v106 | VERIFIED/HIGH | Producer lineage still HOLD |
| WORLD/PUZZLES sound bridge | v107 | VERIFIED exact bytes / HIGH bridge | Full compiler HOLD |
| Source-safe runtime IR | v110-context-v18 | VALIDATED metadata | Excluded binary assets still require local restore |
| KG-001 acceptance contract | v110-context-v18 | ACCEPTED / contract validator | Build has not passed KG-001 yet |
| Godot runtime launch | current analysis env | NOT RUN | Godot unavailable here |

## KG-001 required release gates

`G00` context/evidence integrity; `G01` data validation; `G02` unit/gameplay logic; `G03` exhaustive puzzle state-space; `G04` room/transition state; `G05` trigger semantics; `G06` mock audio event-stream golden tests; `G07` save/load state hashes; `G08` headless synthetic full-demo playthrough; `G09` fresh-checkout build; `G10` final manual sanity check.

The build is eligible for tag `demo-known-good-001` only with all required gates PASS, zero known critical bugs and zero reproducible softlocks. See `docs/KG001_ACCEPTANCE_PLAN.md`.


## v108 KG-001 automation status

| Gate/layer | Status | Evidence boundary |
|---|---|---|
| Canonical DemoState hash | IMPLEMENTED / source-contract checked | Godot runtime hash parity still to execute |
| G02 gameplay logic model | SOURCE-MODEL PASS | Runtime unit execution pending |
| G03 puzzle state-space | SOURCE-MODEL PASS — 63 states, 0 softlocks | Godot headless parity pending |
| G04-G08 runtime chain | PENDING | Next implementation target |


## v109 KG-001 headless status

| Gate/layer | Status | Evidence boundary |
|---|---|---|
| Persistent save/reset/restore | IMPLEMENTED / source-contract checked | Godot runtime execution pending |
| Logical audio capture | IMPLEMENTED / source-contract checked | Does not test WAV playback or Classic spatial parity |
| Headless autoload/Event IR runner | READY / NOT EXECUTED | Requires Godot executable |
| G04/G05 physical rooms/triggers | PENDING | Requires locally restored excluded demo assets |


## v110 KG-001 room/trigger status

| Gate/layer | Status | Evidence boundary |
|---|---|---|
| G04 room transitions | SOURCE_CONTRACT_PASS / runtime pending | Requires restored local R1/R7/R8 GLBs |
| G05 trigger bounds/gates | SOURCE_CONTRACT_PASS / runtime pending | Uses real RoomManager path when executed |
| Missing-asset handling | IMPLEMENTED | Reports BLOCKED_MISSING_ASSETS, not FAIL |
| G08 full synthetic demo | PENDING | Build after v109/v110 runtime pass |
