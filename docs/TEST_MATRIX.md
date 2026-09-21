# OpenAzrael Test Matrix

## Candidate 2 Windows execution — 2026-09-20

**KG-001 Candidate 2 / v116-context-v32: G00-G09 PASS; G10 PENDING_MANUAL_USER.**
Tested source `89ccf775dfd6abc21e6bc69f344fe2d349b4dd70`, Godot `4.7.2.stable.official.ed1daf0bf`.
The clean-checkout suite passed source validation, asset import, v109, v110,
v111 and audio-v116 (62 checks). The exported Windows EXE passed headless and
graphical smoke tests. Instrumented exported-PCK checks passed real floor
support in R1/R7/R8, nonzero Master audio output, cutout materials and F11 ZIP
capture without a gameplay-state hash change. Supplied Sigil icons are verified
inside the executable. Some headless scene tests report non-fatal ObjectDB
cleanup warnings; there are no ERROR or SCRIPT ERROR lines in the passing runs.

Additional integration fixes preserve the authored invisible R8/Object01
entrance support collision, repair empty ambient WAV loop ranges, and retain
Godot numeric typing and runner error handling. The v32 indexed palette rule
preserves the single near-magenta non-key pixel in BLOOS4#.

Candidate 1 manual failure remains historical evidence. Issues #6, #9 and #11
await human retest and remain release blockers. No `demo-known-good-001` tag
is allowed or created. Original Miles parity and complete original renderer
transparency semantics remain HOLD. See `docs/CANDIDATE2_WINDOWS.md` and
`data/tests/kg001_candidate2_windows.json` for details.

**Canonical checkpoint:** `v116-context-v32`

| Area | Current checkpoint | Status | Boundary |
|---|---:|---|---|
| Project context | v116-context-v32 | PASS target | Source/context validation |
| Graphics pipeline | v44 | PASS | Runtime screenshot parity separate |
| Demo coordinate transform | v67 | HIGH | Retail-global still pending |
| Classic audio reference/capture pipeline | v58-v86 | TESTED/HIGH pieces | Genuine original parity UNOBSERVED |
| Gameplay Event IR | v87-v89 | Implemented/Tested | Not all source semantics exact |
| PUZZLES structural grammar | v90-v100 | HIGH structural subsets | Full enclosing grammar HOLD |
| Direct PUZZLES open audit | v103-v105 | HIGH for audited mechanisms | Indirect/custom paths not excluded |
| WORLD.DAT runtime loader | v106 | VERIFIED/HIGH | Producer lineage still HOLD |
| WORLD/PUZZLES sound bridge | v107 | VERIFIED exact bytes / HIGH bridge | Full compiler HOLD |
| WORLD opcode-0x28 record fields | v113 | VERIFIED field identities / ordered 38-of-40 mapping | +17..+26 UNKNOWN/HOLD; full compiler HOLD |
| Source-safe runtime IR | v116-context-v32 | VALIDATED metadata | Excluded binary assets still require local restore |
| KG-001 acceptance contract | v116-context-v32 | ACCEPTED / contract validator | Build has not passed KG-001 yet |
| Godot runtime launch | current analysis env | NOT RUN | Godot unavailable here |

## Current execution summary

| Item | Current state |
|---|---|
| Technical base | v116 |
| Candidate | KG-001 Candidate 3 |
| Candidate diagnostic source contract | PASS |
| Physical audio source contract | **PASS — Issue #9 regression wired** |
| v109 headless runtime | AUTOMATED PASS |
| v110 room/trigger runtime | AUTOMATED PASS |
| v111 full-demo runtime | AUTOMATED PASS |
| audio-v116 physical runtime | AUTOMATED PASS |
| Candidate 3 source CI | PENDING/PASS required at exact HEAD |
| Candidate 3 asset-backed preflight | PENDING — requires v109/v110/v111/audio-v116/physical-v117/well-tongs-v118 PASS |
| G09 fresh-checkout build | PENDING for Candidate 3 |
| Candidate 1 manual observation | **FAIL — Issue #6 floor collision; Issue #9 no audible audio; Issue #11 magenta color-key artifacts** |
| Candidate 2 v32 evidence | HISTORICAL — automated PASS followed by manual traversal FAIL; stale for current source |
| Candidate 3 blocker fixes | SOURCE HARDENED / runtime retest pending |
| G10 manual sanity | **BLOCKED — Candidate 3 preflight/export PASS required; floor/stairs/audio/transparency/keyhole orientation retest pending** |
| Known-good tag | NOT ALLOWED |
| Localization architecture | APPROVED / IMPLEMENTATION DEFERRED |

## KG-001 required release gates

`G00` context/evidence integrity; `G01` data validation; `G02` unit/gameplay logic; `G03` exhaustive puzzle state-space; `G04` room/transition state; `G05` trigger semantics; `G06` logical golden audio events plus physical playback-readiness regression; `G07` save/load state hashes; `G08` headless synthetic full-demo playthrough; `G09` fresh-checkout build; `G10` final manual sanity check.

The build is eligible for tag `demo-known-good-001` only with all required gates PASS, zero known critical bugs and zero reproducible softlocks. See `docs/KG001_ACCEPTANCE_PLAN.md`.


## v108 KG-001 automation status

| Gate/layer | Status | Evidence boundary |
|---|---|---|
| Canonical DemoState hash | IMPLEMENTED / source-contract checked | Godot runtime hash parity still to execute |
| G02 gameplay logic model | SOURCE-MODEL PASS | Runtime v109 PASS |
| G03 puzzle state-space | SOURCE-MODEL PASS — 63 states, 0 softlocks | Godot headless parity PASS |
| G04-G08 runtime chain | PENDING | Next implementation target |


## v109 KG-001 headless status

| Gate/layer | Status | Evidence boundary |
|---|---|---|
| Persistent save/reset/restore | IMPLEMENTED / source-contract checked | Godot runtime PASS |
| Logical audio capture | IMPLEMENTED / source-contract checked | Does not test WAV playback or Classic spatial parity |
| Headless autoload/Event IR runner | READY / NOT EXECUTED | Requires Godot executable |
| G04/G05 physical rooms/triggers | PENDING | Requires locally restored excluded demo assets |


## v110 KG-001 room/trigger status

| Gate/layer | Status | Evidence boundary |
|---|---|---|
| G04 room transitions | AUTOMATED PASS | Requires restored local R1/R7/R8 GLBs |
| G05 trigger bounds/gates | AUTOMATED PASS | Uses real RoomManager path when executed |
| Issue #6 legacy trimesh collision | AUTOMATED PASS | Generated concave collision is two-sided to tolerate legacy winding |
| Issue #6 R1/R7/R8 entry floor-support regression | AUTOMATED PASS | Downward physics probe + real player capsule must settle `is_on_floor()` at spaview/view/Object14 |
| Missing-asset handling | IMPLEMENTED | Reports BLOCKED_MISSING_ASSETS, not FAIL |
| G08 full synthetic demo | PENDING | Build after v109/v110 runtime pass |


## v116 KG-001 legacy color-key transparency — Issue #11

| Layer | Status | Evidence boundary |
|---|---|---|
| Shared color-key rule | INDEXED_SOURCE_CONTRACT_PASS | `#` name + exactly one used palette index matching raw R=255/B=255/G<=8 before RGB expansion |
| AZF Classic PNG output | ASSET-BACKED PASS | Only the exact selected indexed key becomes binary alpha; ordinary palette indices remain opaque |
| XAF -> GLB material | ASSET-BACKED PASS | Keyed RGBA becomes PBR MASK, cutoff 0.5 |
| Demo `#` class registry | 10 candidates / actual corpus audit PASS | Archive + per-AZF hashes bind metadata; no commercial pixels tracked |
| BLOOS4# control | PASS | key index 5; near-magenta non-key index 9 occurs once, proving broad-threshold uniqueness invalid |
| R1 keyhole / tongs | REGRESSION WIRED | KEYHOLE# and TONG6 -> MINETON# must resolve to MASK; KEYHOLE# alone gets FLIP_V_CANDIDATE3_KEYHOLE, TONG6 is negative control |
| Restored-corpus audit | AUTOMATIC WHEN ASSETS PRESENT | 86 PNG set + no residual key magenta |
| Manual visual parity | G10 PENDING | Pink/magenta backgrounds must be absent and R1 keyhole must be upright |
| Complete renderer transparency semantics | HOLD | No broad blending/transparency claim |

## v116 KG-001 physical audio readiness — Issue #9

| Layer | Status | Evidence boundary |
|---|---|---|
| Source contract | SOURCE_CONTRACT_PASS | Tracks ambient IR, physical WAV preflight and Event-IR physical-player wiring |
| Ambient IR | R1=2 / R7=3 / R8=2 | Source-safe recovered metadata; audio payloads remain Git-ignored |
| Master bus / stream / playing checks | AUTOMATED PASS | Headless Godot readiness, not human audibility |
| Event physical player | AUTOMATED PASS | R7_WATER_SWITCHBOARD_SOLVED -> S152V2.WAV probe |
| Human audibility | G10 PENDING | Automated `playing=true` cannot prove speaker/headphone output |
| Original Miles pan/volume parity | HOLD | Separate forensic oracle |

## v111 KG-001 full-demo status

| Gate/layer | Status | Evidence boundary |
|---|---|---|
| G08 production-interaction synthetic route | AUTOMATED PASS | Uses real interaction scripts and RoomManager |
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


## v116 KG-001 Candidate 3 diagnostics

| Layer | Status | Evidence boundary |
|---|---|---|
| Candidate build watermark | SOURCE_CONTRACT_PASS | KG-001 Candidate 3 / v116-context-v32 |
| Fail-fast room/IR preflight | SOURCE_CONTRACT_PASS | Runtime import PASS |
| Golden Event-IR WAV preflight | SOURCE_CONTRACT_PASS | Required only for non-headless Candidate 3 |
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
| Source-frozen v32 Candidate execution | AUTOMATED PASS | Multi-room v110, audio-v116 and indexed color-key validation PASS; manual blocker smoke pending |
