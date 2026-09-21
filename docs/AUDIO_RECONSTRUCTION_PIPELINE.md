# Audio Reconstruction Pipeline — R1 → R7 → R8 Vertical Slice

Status: **PRE-BUILD / SOURCE-SAFE**. This layer extends the existing v21–v116 forensic audio work without changing KG-001 runtime behavior.

## Pipeline
`original payloads -> deterministic import/extraction manifest -> Sound Database -> Original Audio Map -> room/emitter map -> Acoustic Rooms/Graph + Portals -> Classic/Enhanced runtime adapter -> Audio Debug View -> parity/synthetic tests`

## Evidence rules
Original identity, trigger semantics and measured/classic parameters are immutable evidence. Every inferred field carries provenance and confidence. Unknown values remain **HOLD**; no reverb, occlusion or attenuation guess may silently become Classic truth.

## Vertical-slice acceptance
R1/R7/R8 is the only activation target until A01–A12 pass. Synthetic interaction tests must model a player action and assert the complete chain: **action → trigger → audio event/emitter → audible asset request → puzzle/game-state transition**. Traversal trace must cover **R1 → R7 → R1 → R8**.

## Runtime isolation
Classic is the default. Enhanced Spatial is feature-flagged. Switching modes must preserve sound IDs, trigger timing/semantics and gameplay state. Reverb/occlusion are enhanced-only until independently evidenced. Existing v86 unverified Classic renderer HOLD remains unchanged.

## Next runtime gate
After source validation, restore/extract original payloads locally, generate the database/map deterministically, run v109/v110/v111/v112 plus A01–A12, then use Audio Debug View during the real Candidate build. Only empirical Godot playback can promote runtime gates.
