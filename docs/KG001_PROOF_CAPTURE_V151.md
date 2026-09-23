# KG-001 Proof Capture v151

## Goal

Create a short **real runtime** walkthrough video that demonstrates the accepted Candidate 4 demo route without a noclip/fly camera, synthetic imagery or direct gameplay-state injection.

The video is captured from the production player camera while the existing chained PPPV runner performs the same physical actions used for acceptance evidence.

## Fail-closed prerequisites

The capture tool refuses to create a final MP4 unless all of the following are true:

1. the tracked Git worktree is clean;
2. Candidate 4 asset-backed preflight is PASS for the exact current commit;
3. the Candidate 4 frozen-release identity revalidates on the same source tree and runtime asset set;
4. the existing chained PPPV baseline is PASS;
5. PPPV determinism is PASS with at least two identical runs;
6. graphical Godot Movie Maker and ffmpeg are available.

## Capture

Run:

```bash
python tools/capture_candidate4_proof_video.py
```

The tool launches `pppv_playthrough_runner.gd` graphically with Godot Movie Maker, at 1280x720 and 30 fps by default. The production player camera remains active. A small evidence overlay shows the exact Git SHA, freeze receipt hash prefix, current room, PPPV step and current step status.

The chained route is the accepted demo route:

`R1 -> R7 -> R1 -> R8`

and includes the real production interactions/checkpoints defined by the existing PPPV plan.

## Validation after recording

Recording alone is not PASS.

The captured run is independently fed through `tools.remaster_framework.evaluate_playthrough`. Its semantic replay SHA-256 and final-state SHA-256 must match the already-PASS deterministic PPPV baseline. If either differs, the final MP4 is deleted/fails closed.

Only after that check does ffmpeg create:

`.tmp/kg001_proof_capture/OpenAzrael_KG001_Candidate4_Proof.mp4`

The v151 receipt binds the exact source/freeze/preflight identities, PPPV evidence, raw AVI, MP4 and toolchain versions.

## Evidence boundary

This video is intentionally **supplemental evidence**. It demonstrates a real graphical exact-source PPPV traversal on the frozen runtime identity. It does not replace packaged EXE/PCK parity and it does not replace manual G10.

No AI-generated visuals are used.
