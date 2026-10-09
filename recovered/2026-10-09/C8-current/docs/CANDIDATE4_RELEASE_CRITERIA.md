# KG-001 Candidate 4 release criteria

Candidate 4 is the first OpenAzrael demo candidate intended to be fully playable end to end. It MUST NOT be exported merely to validate source changes.

## Evidence tiers

SOURCE CONTRACT PASS, ASSET-BACKED RUNTIME PASS, PACKAGED/EXPORT PASS and MANUAL G10 PASS are separate claims. Passing one tier never promotes another.

Candidate 4 and `demo-known-good-001` remain forbidden until the exact exported EXE/PCK pair has completed every required tier.

## Source and contract identity

`tools/kg001_gate_manifest.py` is the canonical ordered gate declaration used by runner/preflight validators. Candidate 3 and Candidate 4 machine-readable contracts must match it exactly.

The exact Git HEAD/tree used for asset-backed preflight is immutable for the release cycle. Any source change invalidates the preflight/freeze chain and requires a new cycle.

## Source corpus identity

Commercial source payloads may be consumed only through an explicit `--demo-dir` or the verified persistent source registry. Missing registration, source fingerprint drift or corpus-shape mismatch is a hard failure. Commercial and reproducible commercial-derived payload bytes stay outside Git.

## Geometry and traversal

R1, R7 and R8 must use the complete restored demo geometry. The v117-v131 traversal/fidelity stack must pass, including the former R1/Object02 failure point, both R8 stair profiles, all required room transitions and a literal PASS v131 forensic report for R1/R7/R8.

PPPV v2 must exercise production player movement/interactions and produce its required scenario, integrity, playthrough and repeated-determinism evidence. No direct gameplay-state injection is allowed for scenarios intended to simulate a real player.

## Interactions and save/load

v148 requires deterministic selection when the camera starts inside overlapping interactable Area3D volumes while preserving a successful raycast as the primary path.

The legacy save format remains `SAVE%d.dat`, schema `openazrael.demo_save`, version 145. Current saves must roundtrip. Older/unknown versions, corrupt JSON, wrong schema and incompatible canonical state payloads must fail closed unless an explicit migration exists. No migration is currently claimed.

## Audio and music

The canonical 30-WAV demo corpus remains mandatory, followed by human audibility in G10.

Candidate 4 music must bind source XMI SHA-256, SoundFont SHA-256 and output OGG SHA-256. The renderer additionally records FluidSynth identity/version, libsndfile identity, canonical event/timing SHA-256 and pre-encode PCM f32le SHA-256.

Evidence boundary:

- event/timing SHA identifies the codec-independent render schedule;
- PCM SHA identifies the exact produced PCM for that invocation;
- OGG SHA identifies the exact encoded artifact for that invocation;
- cross-platform bit-identical PCM is **not guaranteed**;
- cross-platform bit-identical OGG/container output is **not guaranteed**.

## Frozen release handoff

After a PASS Candidate 4 preflight, run `python tools/freeze_candidate4_release.py`. The source-safe local receipt binds exact commit/tree, preflight receipt SHA-256 and the complete runtime asset identity digest.

`tools/export_candidate4.py` must reject missing/stale freeze receipts and any source-tree, preflight or runtime-asset drift. The exact source may optionally be mirrored as a source-only GitHub artifact using the Candidate 4 source snapshot workflow with an explicit expected SHA.

## Release rule

Candidate 4 requires zero known critical bugs, zero reproducible softlocks, zero failed mandatory gates, clean-checkout reproducibility, exact-head/runtime-asset binding, guarded export/startup smoke, packaged parity/music PASS and complete manual G10 on the exact exported EXE/PCK pair.
