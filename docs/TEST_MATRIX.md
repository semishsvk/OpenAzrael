# OpenAzrael Test Matrix

**Canonical checkpoint:** `v116-context-v29`

| Area | Current checkpoint | Status | Boundary |
|---|---:|---|---|
| Project context | v116-context-v29 | PASS target | Source/context validation |
| Graphics pipeline | v44 | PASS | Runtime screenshot parity separate |
| Demo coordinate transform | v67 | HIGH | Retail-global still pending |
| Classic audio reference/capture pipeline | v58-v86 | TESTED/HIGH pieces | Genuine original parity UNOBSERVED |
| Gameplay Event IR | v87-v89 | Implemented/Tested | Not all source semantics exact |
| PUZZLES structural grammar | v90-v100 | HIGH structural subsets | Full enclosing grammar HOLD |
| Direct PUZZLES open audit | v103-v105 | HIGH for audited mechanisms | Indirect/custom paths not excluded |
| WORLD.DAT runtime loader | v106 | VERIFIED/HIGH | Producer lineage still HOLD |
| WORLD/PUZZLES sound bridge | v107 | VERIFIED exact bytes / HIGH bridge | Full compiler HOLD |
| WORLD opcode-0x28 record fields | v113 | VERIFIED field identities / ordered 38-of-40 mapping | +17..+26 UNKNOWN/HOLD; full compiler HOLD |
| Source-safe runtime IR | v116-context-v29 | VALIDATED metadata | Excluded binary assets still require local restore |
| KG-001 acceptance contract | v116-context-v29 | ACCEPTED / contract validator | Build has not passed KG-001 yet |
| Godot runtime launch | current analysis env | NOT RUN | Godot unavailable here |

## Current execution summary

| Item | Current state |
|---|---|
| Technical base | v116 |
| Candidate | KG-001 Candidate 2 |
| Candidate diagnostic source contract | PASS |
| Physical audio source contract | **PASS — Issue #9 regression wired** |
| v109 headless runtime | NOT_EXECUTED |
| v110 room/trigger runtime | NOT_EXECUTED |
| v111 full-demo runtime | NOT_EXECUTED |
| audio-v116 physical runtime | NOT_EXECUTED |
| G09 fresh-checkout build | PENDING |
| Candidate 1 manual observation | **FAIL — Issue #6 floor collision; Issue #9 no audible audio** |
| Candidate 2 v29 blocker fixes | SOURCE_READY / runtime retest pending |
| G10 manual sanity | **BLOCKED — Issues #6/#9 retest required** |
| Known-good tag | NOT ALLOWED |
| Localization architecture | APPROVED / IMPLEMENTATION DEFERRED |

## KG-001 required release gates

`G00` context/evidence integrity; `G01` data validation; `G02` unit/gameplay logic; `G03` exhaustive puzzle state-space; `G04` room/transition state; `G05` trigger semantics; `G06` logical golden audio events plus physical playback-readiness regression; `G07` save/load state hashes; `G08` headless synthetic full-demo playthrough; `G09` fresh-checkout build; `G10` final manual sanity check.

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
| Issue #6 legacy trimesh collision | SOURCE_CONTRACT_PASS / runtime pending | Generated concave collision is two-sided to tolerate legacy winding |
| Issue #6 R1 floor-support regression | WIRED / runtime pending | Downward physics probe + real player capsule must settle `is_on_floor()` |
| Missing-asset handling | IMPLEMENTED | Reports BLOCKED_MISSING_ASSETS, not FAIL |
| G08 full synthetic demo | PENDING | Build after v109/v110 runtime pass |


## v116 KG-001 physical audio readiness — Issue #9

| Layer | Status | Evidence boundary |
|---|---|---|
| Source contract | SOURCE_CONTRACT_PASS | Tracks ambient IR, physical WAV preflight and Event-IR physical-player wiring |
| Ambient IR | R1=2 / R7=3 / R8=2 | Source-safe recovered metadata; audio payloads remain Git-ignored |
| Master bus / stream / playing checks | WIRED / runtime pending | Headless Godot readiness, not human audibility |
| Event physical player | WIRED / runtime pending | R8_LENS_PLACE -> S152V2.WAV probe |
| Human audibility | G10 PENDING | Automated `playing=true` cannot prove speaker/headphone output |
| Original Miles pan/volume parity | HOLD | Separate forensic oracle |

## v111 KG-001 full-demo status

| Gate/layer | Status | Evidence boundary |
|---|---|---|
| G08 production-interaction synthetic route | SOURCE_CONTRACT_PASS / runtime pending | Uses real interaction scripts and RoomManager |
| Direct gameplay state injection | FORBIDDEN / validated absent | Trigger positioning is synthetic, state effects are production code |
| Final state hash oracle | WIRED | v108 success hash |
| Logical audio oracle | WIRED | S152V2 -> S137 -> S121 -> 799SECDR |
| Consolidated G00-G10 status | PRE_RUNTIME_READY | Final tag forbidden until all gates literal PASS |


## v112 KG-001 candidate workflow

| Layer | Status | Evidence boundary |
|---|---|---|
| One-command candidate runner | SOURCE_CONTRACT_READY | Runtime execution requires Godot |
| Godot restored-asset import | REQUIRED FOR G09 | Import output retained in .tmp/kg001 |
| Git clean before/after | WIRED | Ignored local commercial-derived assets permitted |
| Forbidden tracked payload scan | WIRED | Blocks G09 on violation |
| Runtime evidence promotion | OPTIONAL / EXPLICIT | Happens only after clean-checkout observation |
| G00-G09 evidence-driven status | WIRED | Only recorded PASS promotes a gate |
| G10 manual sanity | CHECKLIST_READY / PENDING_USER | Never auto-promoted |


## v113 WORLD sound-record field closure

| Check | Status | Evidence boundary |
|---|---|---|
| Bound R.EXE / WORLD.DAT / PUZZLES.DAT fingerprints | PASS | Exact v106/v107 source hashes |
| PUZZLES sound records | 40 | Structurally recovered opcode-0x28 population |
| WORLD sound records | 44 | Fixed 27-byte section-6 records |
| Ordered sequence mapping | **38/40 PASS** | LCS/order-sensitive, not free multiset pairing |
| +13 field | **VERIFIED** section-0 object index | Runtime indexes global 0x43890 |
| +15 field | **VERIFIED** demo room/context id | 35 direct XAF + 3 R7 aliases, 0 conflicts |
| +1 field | **VERIFIED** sound stem | Preserved as record+1 and formatted with %s.WAV |
| Dynamic spatial start | VERIFIED control/data flow / HIGH role identity | Handler 0x191E9 -> 0xD155 |
| +17..+26 | UNKNOWN/HOLD | Not consumed by opcode-0x28 handler |
| Source-safe result boundary | PASS | No raw/raw_hex/block_hex/payload bytes committed |


## v114 WORLD section-6 opaque serializer

| Check | Status | Evidence boundary |
|---|---|---|
| Reader chain 0x29E98 -> 0x29CF4 -> 0x29638 | PASS / VERIFIED | Unique direct call chain |
| Writer chain 0x29E40 -> 0x29D74 -> 0x2972C | PASS / VERIFIED | Unique direct call chain |
| 37-byte records | OPAQUE WHOLESALE I/O VERIFIED | 0x25 read/write |
| 27-byte records | OPAQUE WHOLESALE I/O VERIFIED | 0x1B read/write |
| Immediate malloc(27)-style audit | 1 match: reader only | Does not exclude variable/alternate allocation |
| Sound-record tail population | 41 unique / 44; 40 non-zero | Metadata summary only |
| Duplicate semantic groups | 7/7 have varying +17..+26 | Runtime-equivalent stem/object/room grouping |
| 797tap/tapframe2/R8 | 12 records / 12 unique tails | Strong variability control |
| +17..+26 semantics | UNKNOWN/HOLD | Handler non-use + serializer opacity; exact origin not proven |
| Source-safe result boundary | PASS | No raw record/tail payloads committed |


## v115 WORLD action-record lifecycle

| Check | Status | Evidence boundary |
|---|---|---|
| 27-byte insert helper direct callers | 1 / WORLD reader only | Audited direct rel32 CALL class |
| 37-byte insert helper direct callers | 1 / WORLD reader only | Audited direct rel32 CALL class |
| Immediate malloc(27)-style pattern | 1 / reader only | Does not exclude generic/variable/alternate allocation |
| Pending action-group entry | VERIFIED 6 bytes | u16 count + original pointer-array address |
| Pending queue copy of action payload | ABSENT in audited path | Shallow reference only |
| Dispatcher source | VERIFIED original record pointer | Walks original pointer array |
| Opcode-0x28 mutation before consume | NONE in audited prefix | Read-only relative to record |
| Runtime normalization/copy stage | NONE IN AUDITED PATH | WORLD load -> schedule -> dispatch |
| +17..+26 origin | UPSTREAM UNKNOWN/HOLD | Already serialized; runtime does not manufacture |
| Source-safe result boundary | PASS | No raw record bytes committed |


## v116 KG-001 Candidate 2 diagnostics

| Layer | Status | Evidence boundary |
|---|---|---|
| Candidate build watermark | SOURCE_CONTRACT_PASS | KG-001 Candidate 2 / v116-context-v29 |
| Fail-fast room/IR preflight | SOURCE_CONTRACT_PASS | Runtime execution pending |
| Golden Event-IR WAV preflight | SOURCE_CONTRACT_PASS | Required only for non-headless Candidate 1 |
| JSONL event telemetry | SOURCE_CONTRACT_PASS | Persistent log disabled in headless mode |
| Trigger enter/exit telemetry | SOURCE_CONTRACT_PASS | Initial false states seeded without EXIT spam |
| F6 trigger volumes | SOURCE_CONTRACT_PASS | Visualization only; does not alter transition logic |
| F7 Candidate HUD | SOURCE_CONTRACT_PASS | Reads runtime state only |
| F8 audio debug | PRESERVED | Existing v69 path |
| F9 audio parity capture | PRESERVED | Existing v71 path |
| F10 canonical state dump | SOURCE_CONTRACT_PASS | Includes payload/hash, room, player XYZ and last-event context |
| F11 bug-report ZIP | SOURCE_CONTRACT_PASS | Observational capture: screenshot/state/500-event tail/system info; no commercial assets |
| GitHub bug issue form | SOURCE_CONTRACT_PASS | Structured severity/category/reproduction intake |
| Fix -> regression rule | DEFINED | Reproducible fixes require regression evidence at the lowest useful layer |
| v112 candidate source suite integration | PASS | v116 validator appended to SOURCE_COMMANDS |
| v27 manual Candidate execution | **FAIL / Critical Issue #6** | Player fell through floor |
| Corrected v28 Candidate execution | NOT_EXECUTED | Must pass v110 floor regression and manual retest |
