# OpenAzrael Test Matrix

**Current branch:** `integration/kg001-candidate3-pppv-v2`  
**Evidence policy:** SOURCE CONTRACT, ASSET-BACKED RUNTIME, PACKAGED/EXPORT and MANUAL G10 are independent tiers.

## Current release matrix

| Area / gate | Source state | Asset/runtime state | Release boundary |
|---|---|---|---|
| Remaster Framework validate + unit tests | REQUIRED; exact-head PASS observed at `34d5b207…` | N/A | Final source HEAD must be re-observed |
| Candidate 3 contract ↔ runner | Canonical manifest exact-match enforcement | PENDING final asset-backed preflight | No Candidate 3 evidence reused across changed SHA |
| Candidate 4 release contract ↔ preflight | Canonical manifest exact-match enforcement | PENDING | Candidate 4 export forbidden before PASS |
| Verify/Release Orchestrator | SOURCE CONTRACT WIRED; 9 generic unit tests PASS in authoring validation; exact-head CI pending | No asset/runtime execution | FAST is diff-targeted; unknown critical changes escalate; only dual-Python exact-head VERIFY may declare source preflight readiness |
| Trigger v137 | SOURCE workflow PASS observed at `34d5b207…` | Required in canonical runtime list | Production trigger path only |
| Localization v139 | SOURCE workflow PASS observed at `34d5b207…` | Required in canonical runtime list | No source-only PASS promoted to runtime |
| v117 physical traversal / stairs | Source validator wired | PENDING final exact-SHA asset run | Natural player movement and real floor/stair collision |
| v119 R1 Object02 regression | Source validator wired | PENDING final exact-SHA asset run | Critical floor blocker gate |
| v120-v131 geometry/fidelity stack | Source validators wired | PENDING final exact-SHA asset run | v131 R1/R7/R8 report must be literal PASS |
| PPPV v2 | Source/integration contract wired | PENDING final exact-SHA asset run | Suite + integrity + playthrough + repeated determinism |
| InteractionProbe v148 | Source contract previously CI-observed | PENDING final runtime execution | Raycast primary; deterministic overlap fallback |
| Legacy menu toggle v149 | Source contract previously CI-observed | PENDING final runtime execution | No new gameplay scope |
| Save compatibility v150 | SOURCE CONTRACT WIRED; final exact-head CI pending | PENDING final runtime execution | Current v145 save succeeds; invalid/unsupported saves fail closed |
| Inventory HUD v157 | SOURCE CONTRACT PASS on feature branch; exact-head CI pending | PENDING Godot runtime execution | Canonical DemoState inventory -> source-positioned carried-object list; save/load and lens/shield flow regression |
| Candidate 4 music v133-v136 | SOURCE CONTRACT WIRED; final exact-head CI pending | PENDING SoundFont/XMI render + Godot playback | Event/PCM hashes independent of OGG exact-artifact SHA |
| Candidate 4 frozen handoff | SOURCE CONTRACT WIRED | Runs only after PASS preflight | Commit/tree + preflight SHA + complete runtime asset digest |
| Candidate 4 packaged/export | N/A | PENDING | Guarded EXE/PCK, startup smoke, packaged parity/music |
| G10 manual | N/A | PENDING | Human end-to-end exact export; release-blocking |
| `demo-known-good-001` | NOT ALLOWED | NOT ALLOWED | Only after every required tier PASS |

## Save/load v150 regression cases

| Case | Expected result |
|---|---|
| Current schema/version | PASS roundtrip; canonical state, room and player pose restored |
| Older version | FAIL_CLOSED; no migration inferred |
| Unknown future version | FAIL_CLOSED |
| Corrupt JSON | FAIL_CLOSED |
| Wrong schema | FAIL_CLOSED |
| Incompatible canonical state payload | FAIL_CLOSED without live-state/room/position mutation |

The filename pattern remains `SAVE%d.dat` and slot names remain FILE ALPHA through FILE EPSILON.

## Candidate 4 music evidence

Per rendered track the receipt records source XMI SHA-256, canonical event/timing SHA-256, pre-encode PCM f32le SHA-256 and exact OGG SHA-256. The receipt also binds the SoundFont and renderer/codec identities.

Cross-platform PCM bit identity is **not guaranteed** and cross-platform OGG byte identity is **not guaranteed**. This prevents an exact-artifact hash from being misrepresented as a universal codec determinism guarantee.

## Historical evidence

Candidate 2 Windows automated evidence remains historical only and is stale for the current integration SHA. Candidate 1/2 manual failures that motivated floor/audio/transparency/stair fixes remain relevant regression provenance, not current Candidate 4 PASS evidence.

## KG-001 release rule

Required gates remain G00-G10. Candidate 4/KG-001 is eligible for Known Good only after zero known critical bugs, zero reproducible softlocks, literal PASS for every required current-SHA source/runtime/packaged gate, and a complete manual G10 on the exact exported EXE/PCK pair.
