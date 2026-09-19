# OpenAzrael Texture Lab — RT-POC-01

**Status:** SOURCE-SAFE TOOLING TESTED / REAL MATHEMATICAL BAKE-OFF EXECUTED / STRUCTURAL BASELINE CALIBRATED / GODOT LAB SOURCE-READY / AI BAKE-OFF PENDING  
**Scope:** presentation tooling only; no gameplay/runtime-semantic changes.

## Purpose

RT-POC-01 establishes a repository-safe texture experiment pipeline around the existing v44 Classic graphics corpus. The source corpus under `assets/textures/classic/` remains local/excluded. Generated pixels also remain local/excluded. Git contains only tools, configuration, tests, workflow metadata and compact reports/fingerprints.

Presentation tiers are:

1. **Classic** — decoded original-reference PNGs.
2. **Enhanced** — deterministic mathematical reconstruction.
3. **AI Restored** — constrained learned restoration/upscale.
4. **AI Recreated** — image-conditioned generative reconstruction.

None of these tiers changes gameplay, geometry, UVs, collision or recovered world/puzzle identifiers.

## Tools

### `oa_tex_scan.py`
Scans local Classic PNGs and writes a metadata-only manifest. Default expected demo count is 86.

### `oa_tex_enhance.py`
Creates deterministic 4x candidates using Pillow nearest, bicubic and Lanczos resampling. An external xBRZ executable can be integrated only by an explicitly pinned command template.

### `oa_tex_validate.py`
Checks target dimensions and records observational fidelity metrics: Lanczos round-trip MAE, optional SSIM when scikit-image is available, mean-channel drift, alpha/color-key safety and raw edge-seam MAE. Missing candidates are technical failures.

### `oa_tex_compare.py`
Creates a local visual comparison sheet across Classic, mathematical Enhanced, AI Restored and AI Recreated variants.

### `oa_tex_tile.py`
Creates a 3x3 (or configurable) repeated texture preview for direct seam/tiling inspection. The image remains repository-ignored.

### `oa_tex_sampling_audit.py`
Audits the canonical POC selection against the real v44 R1/R7/R8 manifests and GLBs. It records primitive usage plus aggregate UV bounds. UVs significantly outside 0..1 are evidence of repeat sampling under the v44 GLB default sampler; merely spanning almost 0..1 is recorded for seam review but is not automatically called tileable.

### `oa_tex_structural_drift.py`
Measures composition/layout drift after a generated candidate is downscaled back to Classic resolution. The primary signal is low-frequency luminance MAE, which intentionally ignores much of the newly generated microdetail and reacts strongly to moved doors, openings, large tonal masses and other composition changes. Edge-map drift, round-trip RGBA MAE and alpha-silhouette mismatch are recorded alongside it.

### `oa_tex_calibrate_drift.py`
Builds the reference structural-drift envelope from deterministic Enhanced variants. The committed POC baseline is `data/texture_lab/rt_poc_01_drift_baseline.json`. It is a calibration reference, not an automatic AI acceptance threshold.

### `oa_tex_run_poc.py`
Runs the canonical 12-texture mathematical RT-POC-01 selection in one command and produces nearest/bicubic/Lanczos variants plus observational metrics.

```bash
python tools/texture_lab/oa_tex_run_poc.py
```

The canonical selection is stored in `config/rt_poc_01_selection.json`. It contains four R1, four R7 and four R8 textures covering rock/organic surface, architecture, parchment, hard-edge mask, carved wall, character detail, mechanism, floor, glass, high-detail mural and text/decorative content.

### Pinned Real-ESRGAN runtime

`config/model_registry.json` pins the primary AI Restored runtime identity:

- upstream source: `xinntao/Real-ESRGAN` tag `v0.3.0`, exact commit `fa4c8a03ae3dbc9ea6ed471a6ab5da94ac15c2ea`;
- model: `RealESRGAN_x4plus`;
- official checkpoint release: `v0.1.0`;
- exact checkpoint size: `67040989` bytes;
- SHA-256: `4fa0d38905f75ac06eb49a7951b426670021be3018265fd191d2125df9d682f1`;
- inference baseline: 4x, `tile=0`, FP32.

`oa_tex_realesrgan_bootstrap.py` can clone/download the pinned runtime on a network-enabled development machine and refuses a checkpoint identity mismatch. `oa_tex_realesrgan_doctor.py` records Python/platform/module/source/checkpoint readiness before a real bake-off.

Typical local preparation:

```bash
python tools/texture_lab/oa_tex_realesrgan_bootstrap.py \
  --clone-upstream \
  --download-model

python tools/texture_lab/oa_tex_realesrgan_doctor.py
```

Dependency installation is deliberately explicit (`--install-python-deps`) so the tool never silently rewrites an existing Python environment.

### `oa_tex_restore.py`
Supports a pinned official Real-ESRGAN Python backend plus a fallback command-template backend. For a registered model, the adapter itself re-verifies the pinned upstream version, checkpoint byte size and SHA-256 immediately before inference; a mismatch aborts the run. The preferred POC path records the exact checkpoint SHA-256, tile setting, precision mode and denoise strength. `tile=0` is the default fidelity path; tiling is a resource fallback, not the baseline.

Legacy color-key candidates are converted to alpha-safe input before the backend and the exact source-derived binary mask is reapplied afterward.

### Pinned Qwen / ComfyUI runtime

`config/qwen_2511_contract.json` pins the canonical single-image Qwen-Image-Edit-2511 experiment: fixed seed 734234, 40 steps, CFG 4.0, Euler/simple sampling, no Lightning LoRA, exact model filenames and model-file SHA-256 identities. `workflows/qwen_2511_openazrael_api.json` is the repository-owned API-format graph derived from the current official ComfyUI workflow contract.

`oa_tex_comfy_doctor.py` first checks a running ComfyUI server through `/system_stats` and `/object_info` and requires all node classes/input schemas used by the graph. `oa_tex_qwen_preflight.py` then validates the exact workflow topology, node bindings, sampler settings, model filenames and—when a ComfyUI root is supplied—the exact model sizes/hashes.

AI Recreated is conditioned on the 4x Enhanced canvas (Lanczos in RT-POC-01), while Classic remains the source of truth for structural QA and legacy alpha masks. This reduces the amount of geometry the model has to infer from low-resolution source pixels.

### `oa_tex_recreate.py`
Generic ComfyUI API runner. It consumes an API-format exported workflow and patches explicit Load Image / prompt / seed nodes supplied on the command line. Each job record fingerprints the workflow template, submitted workflow, source, output and explicitly supplied model files.

Legacy color-key candidates follow the same alpha-lock policy as AI Restored: alpha-safe source goes into the model and the exact source silhouette is reapplied to the generated output.

`config/ai_backends.json` defines the POC backend matrix. `profiles/recreate_profiles.json` plus `oa_tex_prompt.py` produce consistent preservation-first prompts from each selected texture's content class; prompts remain input evidence for the experiment, not proof of visual fidelity.

### Godot Texture Lab
`tools/texture_lab/godot/texture_lab.tscn` is an isolated comparison scene, not the normal OpenAzrael main scene. It loads local texture pixels at runtime and supports:

- Left/Right: previous/next canonical POC texture;
- 1/2/3/4: Classic / Enhanced / AI Restored / AI Recreated;
- Q/W/E: nearest / bicubic / Lanczos Enhanced variants;
- T: 1x1 / 2x2 / 4x4 repeated display;
- L: unshaded vs directional-light inspection;
- S: local screenshot.

The scene does not access DemoState, CandidateDiagnostics or RoomManager and does not mutate gameplay state. `validate_godot_lab.py` enforces this source contract. Actual Godot execution remains pending on a machine with Godot and the ignored local texture corpus.

## Real mathematical POC observation

A real 12-texture bake-off was executed against the restored v44 Classic corpus on 2026-09-19. All 36 nearest/bicubic/Lanczos outputs were produced at 4x dimensions.

Round-trip similarity predictably favors nearest-neighbour because it preserves the original pixel lattice most directly. This is **not** treated as a visual-quality winner.

A follow-up visual QA pass identified legacy `#` textures containing quantized magenta (`R/B >= 248`, `G <= 12`). RT-POC-01 now treats only `#` assets with observed magenta as conservative color-key candidates: magenta becomes alpha=0, filtered RGB uses premultiplied alpha, and the deterministic Enhanced tier restores the alpha mask with nearest-neighbour. The validator rejects visible magenta bleed and non-binary alpha for these candidates. This is a presentation-safety rule, not a claim that complete original-renderer transparency semantics are recovered.

Visual inspection also confirms why the selection must remain content-aware: hard-edge/mask content benefits from exact edge preservation, while photographic/organic/architectural surfaces can benefit from smoother high-quality reconstruction. No global mathematical method is promoted by RT-POC-01.

## AI asset eligibility policy

The canonical 12-texture set is not sent blindly through every AI backend.

- **AI Restored:** 11/12 eligible. `KEYHOLE#` is skipped and remains a deterministic Enhanced/nearest asset.
- **AI Recreated:** 10/12 eligible. `KEYHOLE#` is skipped for exact-mask fidelity and `SHIELD1` is skipped because unconstrained generative editing can rewrite the original lettering.
- `BAPFLOR#` requires exact alpha lock plus U/V seam review.
- `BAPTAP` requires atlas-boundary and depicted-content review.
- `WEL_PUZ1` requires puzzle-geometry review.

`oa_tex_ai_bakeoff.py` enforces this policy and supports `--dry-run`, so the exact generation/QA command plan can be inspected before any model is executed. No generated asset is automatically promoted to production.

## Structural-drift baseline

The 36 alpha-safe deterministic candidates establish the first reference envelope for a layout-preserving transformation:

- low-frequency luminance MAE, mean: **0.109995 / 255**;
- low-frequency luminance MAE, p95: **0.228836 / 255**;
- low-frequency luminance MAE, maximum: **0.365784 / 255**;
- edge-map MAE, mean: **2.017998 / 255**;
- edge-map MAE, maximum: **6.469116 / 255**.

Low-frequency drift is the primary future AI composition signal. Edge drift is deliberately observational because legitimate AI-created microdetail can increase edge energy. For conservative legacy color-key assets, alpha-silhouette mismatch remains expected at zero.

These values are **not** hard AI pass/fail limits. They define what ordinary deterministic reconstruction does to the same assets and give the AI review a concrete reference scale.

## Repository safety

Classic decoded PNGs, all generated Enhanced/AI pixels and comparison/tile sheets remain outside Git. Metadata-only manifests/reports may be committed only after review.

## Test policy

`tests/test_texture_lab_rt_poc_01.py` uses synthetic fixtures and checks scan/alpha behavior, deterministic byte-identical upscale output, expected dimensions, legacy color-key safety, AI alpha-mask reapplication, structural-drift displacement sensitivity, stable metrics and tile-preview dimensions. GitHub Actions executes the source-safe suite on Python 3.11 and 3.12 and runs the Godot Texture Lab source-contract validator.

## Next execution step

1. bootstrap/doctor the pinned Real-ESRGAN v0.3.0 + x4plus runtime on the development machine;
2. run the pinned checkpoint on the 11 AI-Restored-eligible textures;
3. run `oa_tex_structural_drift.py` and compare AI Restored results with the mathematical baseline;
4. export a fixed-seed API-format ComfyUI workflow for the selected image-edit model and run AI Recreated;
5. apply the same structural, color-key, seam and text/mask review;
6. compare Classic / Enhanced / AI Restored / AI Recreated using identical source IDs;
7. execute the dedicated Godot Texture Lab scene on the development machine before production-wide conversion.

RT-POC-01 remains observational: it does not replace Classic evidence or automatically select a production winner.
