# OpenAzrael v112 — one-command KG-001 candidate runner

v112 turns the prepared KG-001 layers into one reproducible candidate workflow.

## Default workflow

Run:

    python tools/run_kg001_candidate_v112.py

The tool executes the source/context validators, discovers Godot from --godot / GODOT_BIN / godot4 / godot, executes v109, imports restored room assets with Godot when present, and then executes v110/v111, the audio-v116 physical playback-readiness regression, the v117 physical traversal regression, and the v118 R7 well+tongs animation-trigger regression. Source validation also includes the Issue #11 indexed-palette legacy color-key regression and automatically becomes asset-backed when restored Classic textures are present.

All temporary evidence goes under .tmp/kg001/, which is ignored by Git.

## Fresh-checkout gate

For G09 use:

    python tools/run_kg001_candidate_v112.py --fresh-checkout

Fresh-checkout PASS requires all of the following simultaneously:
- clean Git worktree before the suite;
- clean Git worktree after the suite;
- no forbidden commercial/raw paths tracked by Git;
- source validators PASS;
- Godot found;
- Godot room-asset import PASS;
- v109, v110, v111, audio-v116, physical-traversal-v117 and well-tongs-v118 runtime status all PASS;
- R1/R7/R8 room assets present locally;
- those local room assets are ignored by Git.

A missing Godot binary or missing room assets cannot accidentally become PASS.

## Promoting evidence

After a successful candidate run, optionally use:

    python tools/run_kg001_candidate_v112.py --fresh-checkout --promote-results

The tool records the clean-state G09 result first, then copies summarized v109/v110/v111/audio-v116/physical-v117 runtime/source/fresh-checkout JSON into data/tests for review and commit. The promotion intentionally makes the source checkout dirty after the G09 observation; that does not rewrite the already-recorded clean_before/clean_after evidence.

G10 manual sanity remains separate and cannot be auto-promoted by this tool.


## Physical audio boundary

The audio-v116 runner checks that the Candidate can physically load and start its required audio resources: Master-bus routing, recovered ambient emitters and a real Event-IR AudioStreamPlayer. It does not prove speaker/headphone audibility and does not prove original Miles pan/volume parity. G10 must still confirm that the user actually hears expected ambient and event audio.


## Legacy color-key boundary

Issue #11 is validated during the source phase. The validator binds the real 86-AZF metadata audit and always exercises a synthetic raw source-sentinel mask and a synthetic XAF->GLB MASK material. When the local Candidate corpus has been restored, the same command audits all 86 Classic PNGs, the complete ten-name `#` candidate class with single-sentinel evidence, and the R1 KEYHOLE#/TONG6 mappings and exact single-key-index evidence. Final visual acceptance remains manual in G10; complete original transparency/blending semantics remain HOLD.


## Physical traversal boundary

The v117 runner closes a false-positive gap discovered during Candidate 2 manual testing. Earlier automation could PASS by raycasting a floor, placing the player slightly above that point, and waiting while stationary; the full-demo runner also teleported directly to trigger centroids.

v117 instead loads the real main scene and production Player, drives `move_forward` / `move_back` through Godot Input actions across the canonical R1 starting floor, and measures fall-through, horizontal progress and floor-contact ratio. It then derives tread levels directly from the imported R8 `step011__mesh` and `stairs__STAIR2` meshes and drives the same CharacterBody3D up and down both real stair profiles. The first covers the lower ~5-unit risers; the main staircase covers ~12.6-unit risers and is the stronger step-up regression. No synthetic proxy stairs are accepted.

A v110 PASS from Candidate 2 predates this traversal contract and is therefore insufficient for a new G04 PASS without a current v117 runtime result.


## Well+tongs recovered-effect boundary

The v118 runner closes the Candidate 2 blind spot using the official demo binaries rather than an invented visual interpolation. The recovered compiled WORLD group executes, in order: remove `R7Key`, play the original `979TONGS.WAV`, add `R7Key`, remove transient `RustyTongR6`, and consume inventory `TONG6`; the normal TAKE completion then moves the Well Key into inventory and sets `R7KeyTake/R7key`.

The group contains no transform/rotation opcode. Therefore v118 asserts the exact action trace, original sample identity/duration, tongs consumption and final key state. It deliberately rejects an invented Tween as a claim of demo fidelity. Any generic HUD/inventory-hand motion outside this recovered WORLD/PUZZLES action stream remains unobserved/HOLD.

