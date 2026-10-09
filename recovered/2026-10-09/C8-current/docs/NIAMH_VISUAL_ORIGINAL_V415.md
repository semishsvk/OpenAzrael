# OpenAzrael C8 v415 — Niamh source-bound visual calibration

**Acceptance scope:** `SOURCE_RUNTIME_PASS + ORIGINAL_NATIVE_STATIC_VISUAL_IMPROVEMENT`.
**Not accepted:** full gameplay animation fidelity, audio fidelity, Retail reconstruction,
public release or Candidate 8 promotion.

## Scope and provenance

The authoritative ATDEMO `R.EXE`, `TEXTURES/NIAMH.XAF`, `NIAMH.ANI`,
R7 geometry and source event graph remain read-only. Six real 640×480 native
DOSBox-X captures of Niamh at the original Well Room, `r_003` through
`r_008` from `original_niamh_visible_v397`, are source identity-checked
by SHA-256 in `data/reconstruction/niamh_visual_calibration_v415.json`.

The original camera comes from authentic original DOSBox-X save memory
player pose (R7 original eye `7.648277, 4.204147, 3.914585` and
forward vector `-0.913545, 0, 0.406737`). Godot uses the actual
**production Player/Camera3D**, including its existing negative-X
basis reflection and original 552×280 3D window. Previous generic
FOV experiments were not the production camera and do not justify
altering world orientation, input, collision or HUD.

Original vs unchanged Godot background registration, without Niamh:

| Source | Luminance correlation | Edge correlation |
|---|---:|---:|
| R1 | 0.96692 | 0.88459 |
| R7 | 0.97282 | 0.87007 |

These checks exclude original HUD text and, for R7, the original
ghost actor's silhouette; they do **not** mean pixel-exact 3D fidelity.
A deliberately horizontally mirrored render and wrong screen crop
both fail the camera registration threshold.

## Bounded visual-fit result

At original Niamh's R7 snapshot, the original authored GLB placement
proxy `nibody` is `(-107.138, -34.5992, 63.9427)`, and the R7
source well root `wel_well__WELL_WELLWALL` is
`(-99.226, -36.486, 38.004)`.

The experimental source-hierarchy visual placement is:

- root XZ = source well's original world XZ;
- root Y = original `nibody` proxy Y + **40 world units**;
- model yaw = **90°**;
- source `NIAMH.XAF` geometry and `NOLOOP1/REST/NOLOOP2` clips unchanged;
- all 19 source character material surfaces remain opaque and
  depth-tested (no fabricated see-through walls).

The 40-unit value is an **empirical six-frame registered-screen fit**,
not the meaning of `NIAMH.ANI HEIGHT 33`, nor a general source XAF
transform contract. It is restricted to Demo R7. The v415 contract
carries SHA-256 source fingerprints, exact object names, camera
evidence and fail-closed range checks; invalid source references
leave the source pose intact and report HOLD.

Using the native six original stills and an actual fresh Godot
production camera source framebuffer, mean absolute RGB error inside
the fixed actor ROI improved by **31.5425%**, worst sample
**27.91%**, versus the same Godot scene with Niamh invisible.
The source stage's calibration-only search returned approx 34.274%
mean improvement; those are different comparisons and must not
be conflated. These are not animation-cadence or pixel-perfect scores.

## Acceptance and negative controls

Source-contract test `tools/test_niamh_visual_calibration_v415.py`
PASS: 10/10. Godot renderer and source placement test
`scripts/kg001_niamh_visual_runner_v415.gd` PASS: 53/53.
`tools/validate_niamh_native_composition_v415.py --fresh`
PASS: 6 SHA-pinned original captures, fail-closed if native captures
are missing, and a negative baseline without any Niamh.
`tools/test_original_player_camera_memory_v408.py` PASS: 43 memory
and negative-integrity checks across six source snapshots.
`tools/test_original_production_camera_v410.py --fresh`
PASS: R1 and R7, including mirrored and rescaled negative controls.
Main Candidate 8 regression: **27/27 groups PASS** with no new
loss of auto-trigger, one-shot save/load, R7 interactions or full-demo
traversal.

No `project.godot`, `export_presets.cfg`, source NIAMH files,
original runtime captures or proprietary original audio are modified
or added to source control.

## Remaining blockers / promotion policy

**HOLD:** original Niamh `NOLOOP1→REST→NOLOOP2` exact frame/tick
timing; original Miles PCM audio from emulated runtime (native AVI
tracks remain silent while `DIG.INI/MDI.INI` are not configured);
translucency and original draw depth mechanism independently verified
in retail; accurate character spatial origin in the source engine
(not merely visual-fit over the model proxy); full demo optical,
dialogue and animation replay comparison; public release safety
(overlarge Retail K001 tracked GLBs); Retail-specific independent
corpus verification; complete final Candidate 8 release.

Do not promote static visual registration or a passing regression
campaign to `FIDELITY_VERIFIED` without original-runtime input replay
and time-correlated frame comparisons.
