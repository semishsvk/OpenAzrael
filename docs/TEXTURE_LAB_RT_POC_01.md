# OpenAzrael Texture Lab — RT-POC-01

**Status:** SOURCE-SAFE TOOLING TESTED / REAL MATHEMATICAL BAKE-OFF EXECUTED / STRUCTURAL BASELINE CALIBRATED / AI RUNTIME CONTRACTS READY / GODOT LAB SOURCE-READY / REAL AI OUTPUTS PENDING  
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
Checks target dimensions and records observational fidelity metrics: Lanczos round-trip MAE, optional SSIM when scikit-image is available, mean-channel drift, alpha/color-key safety and edge-seam MAE. Seam QA now records both the Classic source seam and generated candidate seam plus source-relative U/V delta and ratio. These seam deltas are observational, not automatic pass/fail thresholds. Missing candidates are technical failures.

### `oa_tex_compare.py`
Creates a local visual comparison sheet across Classic, mathematical Enhanced, AI Restored and AI Recreated variants. Review rendering preserves each texture's aspect ratio instead of stretching it to a square; transparent content is composited over a neutral checkerboard so mask/alpha defects remain visible.

### `oa_tex_review_pack.py`
Builds the stage-scoped manual visual-review evidence after AI generation and QA. For every generated candidate it creates an aspect-ratio-safe full comparison sheet plus a deterministic three-region detail sheet against Classic and deterministic Enhanced variants; textures with observed repeat sampling additionally receive a 3x3 seam/tile preview. The manifest fingerprints the Classic source, AI candidate and every rendered review artifact. These files remain local/ignored, but stage approval is bound to their hashes so changed pixels or changed review imagery invalidate an old receipt.

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

### Source-safe mathematical toolchain

The deterministic Enhanced reference is now pinned to `Pillow==12.3.0` through `tools/texture_lab/requirements-source-safe.txt`. `oa_tex_run_poc.py` and `oa_tex_calibrate_drift.py` refuse to run under another Pillow version. The recalibrated drift baseline schema records Pillow and Python versions.

The earlier committed numerical envelope remains useful as historical observational evidence, but a real AI stage is intentionally blocked by `oa_tex_local_preflight.py` until the Enhanced set and drift baseline have been regenerated under the pinned toolchain.

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

### `oa_tex_qwen_bootstrap.py`
Plans, resumably downloads and verifies the three pinned Qwen-Image-Edit-2511 ComfyUI model files. Transfers use `.partial` files and HTTP Range where supported, restart safely when a server ignores Range, and promote a partial file to its final model path only after exact byte-size and SHA-256 verification. Existing invalid final files are not overwritten unless explicitly requested. Optional Hugging Face authentication is read from an environment variable rather than stored in repository data.

The bootstrap is an installation helper only. `oa_tex_qwen_preflight.py` remains mandatory because it independently validates workflow topology, sampler contract, model filenames/hashes and runtime bindings before generation.

### `oa_tex_recreate.py`
Generic ComfyUI API runner. It consumes an API-format workflow and patches explicit Load Image / positive prompt / negative prompt / seed nodes. The canonical OpenAzrael graph is single-image and receives the deterministic 4× Enhanced canvas (Lanczos for RT-POC-01) as its conditioning image; Classic remains the structural/alpha source of truth. Each job record fingerprints the workflow template, submitted workflow, source, output and explicitly supplied model files.

Legacy color-key candidates follow the same alpha-lock policy as AI Restored: alpha-safe source goes into the model and the exact source silhouette is reapplied to the generated output.

`config/ai_backends.json` defines the POC backend matrix. `profiles/recreate_profiles.json` plus `oa_tex_prompt.py` produce consistent preservation-first prompts from each selected texture's content class; prompts remain input evidence for the experiment, not proof of visual fidelity.

### Godot Texture Lab
`tools/texture_lab/godot/texture_lab.tscn` is an isolated comparison scene, not the normal OpenAzrael main scene. It loads local texture pixels at runtime and supports:

- Left/Right: previous/next canonical POC texture;
- 1/2/3/4: select the active/candidate tier: Classic / Enhanced / AI Restored / AI Recreated;
- B: toggle isolated side-by-side A/B comparison;
- R: cycle the A/reference tier while B is active;
- P: reload/toggle the local resolved Remastered runtime profile;
- Q/W/E: nearest / bicubic / Lanczos Enhanced variants;
- T: 1x1 / 2x2 / 4x4 repeated display;
- L: unshaded vs directional-light inspection;
- S: local screenshot, including reference-vs-candidate tier names in A/B mode.

The scene does not access DemoState, CandidateDiagnostics or RoomManager and does not mutate gameplay state. A/B mode uses two isolated QuadMesh surfaces with the same tile and lighting state, so the comparison changes presentation only. `validate_godot_lab.py` enforces this source contract. Actual Godot execution remains pending on a machine with Godot and the ignored local texture corpus.

### `oa_tex_run_summary.py`
Builds a single manual-review handoff from the completed named stage evidence. It collects evidence status, low-frequency drift, source-relative seam deltas, review attention and the exact candidate/full/detail/tile paths. The summary explicitly carries `automatic_quality_verdict=false` and `automatic_stage_approval=false`. Every named AI bake-off appends this as its final source-controlled orchestration step.

### `oa_tex_first_run.py`
Cross-platform launchpad for the first real AI Restored execution. It separates source status, deterministic-baseline preparation, pinned Real-ESRGAN bootstrap and the canonical `restored_smoke_1` run. The launchpad never auto-selects a PyTorch/CUDA build; backend readiness remains the responsibility of the Real-ESRGAN doctor. A dry-run mode is covered by CI.

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

## Staged AI execution

`config/ai_smoke_sets.json` defines the required execution order so a broken backend does not waste a full batch:

1. `restored_smoke_1` — CORIROCK only;
2. `restored_smoke_4` — organic surface, puzzle, keyed/repeated floor, text;
3. `restored_full` — all 11 Restored-eligible assets;
4. `recreated_smoke_1` — CORIROCK only;
5. `recreated_smoke_4` — organic, architecture, puzzle and exact-alpha/repeat cases;
6. `recreated_atlas` — BAPTAP quarter-isolation test;
7. `recreated_full` — all 10 Recreated-eligible assets.

Examples after the corresponding runtime doctor passes:

```bash
python tools/texture_lab/oa_tex_ai_bakeoff.py restored \
  --preset restored_smoke_1 \
  --realesrgan-root .local/texture_lab/realesrgan/Real-ESRGAN \
  --model-path .local/texture_lab/realesrgan/weights/RealESRGAN_x4plus.pth
```

With ComfyUI already running on the default local API port:

```bash
python tools/texture_lab/oa_tex_ai_bakeoff.py recreated \
  --preset recreated_smoke_1 \
  --comfy-root /path/to/ComfyUI
```

Named staged runs are isolated under `.local/texture_lab/runs/rt_poc_01/<preset>/` and run, in order: prerequisite stage gate → pinned-toolchain/local input preflight → backend doctor/preflight → generation → hard technical QA → structural-drift QA → observational review queue. A later preset requires a current manual approval receipt for the prerequisite stage(s).

### BAPTAP atlas isolation

R8 geometry provides four non-overlapping U regions for BAPTAP: tapestry1 ≈ 0.001–0.245, tapestry2 ≈ 0.247–0.497, tapestry3 ≈ 0.499–0.745 and tapestry4 ≈ 0.746–1.000. RT-POC-01 therefore treats the 512×256 Classic atlas as four exact 128×256 quarters (and the 2048×1024 Enhanced atlas as four 512×1024 quarters).

`oa_tex_atlas.py` performs exact equal-quarter split/stitch. During AI Recreated, each BAPTAP quarter is conditioned and generated independently; only then are the four outputs stitched back at the exact 25% boundaries. Unit tests require split→stitch pixel identity before any AI model is involved.

### Manual review queue

`oa_tex_review_report.py` converts structural-drift output plus asset policy/sampling evidence into a stage-scoped manual QA queue. It reports drift ratios against the deterministic p95/max and carries through alpha, seam, atlas, puzzle, artwork and text review requirements. `oa_tex_review_pack.py` then renders the concrete visual evidence to inspect: Classic/Enhanced/AI comparison sheets for every selected texture and 3x3 repeated previews where repeat sampling was observed. `oa_tex_stage_gate.py` records an explicit manual approval receipt only after the stage has complete local-preflight, runtime, technical, structural, generation, review-queue and visual-review-pack evidence; the receipt fingerprints those artifacts and the generated output hashes. It deliberately never promotes a generated asset automatically.

## Runtime presentation manifest

`oa_tex_runtime_manifest.py` is the data-only bridge between reviewed Texture Lab selections and a future presentation runtime. It emits local ignored manifests using the schema `openazrael.texture_lab.runtime_texture_manifest.v1`.

Supported profiles:

- **Classic** — resolves every texture to its immutable Classic PNG;
- **Enhanced** — resolves to the explicitly requested deterministic method; classes marked `enhanced_nearest` are forced to nearest for hard-edge safety;
- **Remastered** — resolves only current PASS production selections to AI Restored/Recreated candidates. Missing selections or stale selections resolve to Classic, never to an unreviewed generated file.

The manifest records each resolution reason, selected tier, file-presence state and aggregate fallback/stale/missing counts. `--strict` turns missing files and stale Remastered selections into a HOLD exit status.

The isolated Godot Texture Lab can preview the local Remastered runtime manifest with **P**. The Godot resolver accepts only schema-v1 manifests with `automatic_promotion=false`, only `res://assets/textures/*.png` paths, and rejects path traversal. It never reads the production-selection registry or stage-approval data directly.

This keeps the boundary explicit:

**audit/selection evidence → validated runtime manifest → presentation resolver**

rather than allowing gameplay/presentation code to inspect experiment directories.

## Runtime export integrity bridge

The runtime presentation manifest now fingerprints every resolved texture file (SHA-256 + byte size) and its selection/policy/production-registry inputs. Explicit production selections additionally record whether the selected candidate hash matches the resolved file hash.

`oa_tex_runtime_verify.py` is the pre-export integrity gate:

- **PASS** — manifest schema/policy is valid, all inputs still match, every resolved path is safe/present and all hashes/sizes match;
- **STALE** — files or source inputs changed after manifest generation;
- **HOLD** — manifest is missing/invalid, a path is unsafe, or a resolved texture is missing.

`oa_tex_runtime_export.py` refuses to compile unless verification is PASS. On success it creates a local static Godot-friendly texture map plus `runtime_export_snapshot.json`, fingerprinting both the source manifest and generated map. It copies no commercial/generated pixels.

The future exported runtime loader contract lives in `godot/runtime_texture_resource_loader.gd`. It validates the safe `res://assets/textures/` namespace and uses `ResourceLoader` to obtain `Texture2D` resources. Raw FileAccess/SHA hashing is intentionally limited to development/pre-export verification because Godot's import/export pipeline may replace source image files with imported resources.

## Structured manual review contract

Stage approval is no longer based on a free-form note alone. `oa_tex_manual_review.py` creates a per-texture review record bound to the current review queue, review pack and candidate hashes.

Every reviewed texture always requires checks for:

- composition/geometry preservation;
- no invented objects, symbols or text;
- plausible material/detail reconstruction;
- acceptable detail artifacts;
- alpha/mask boundaries;
- gameplay-scale appearance.

Policy/evidence adds required checks when relevant for repeated seams, exact text/layout, artwork figures/objects, puzzle/special geometry, atlas boundaries and alpha-policy constraints.

A texture may be `ACCEPTED_FOR_STAGE` only when every required check is explicitly `true`. `HOLD` and `REJECTED` require a note. A stage receives manual-review PASS only when every expected texture is accepted, every required check passes, candidate hashes remain current and the underlying review queue/pack fingerprints still match.

`oa_tex_stage_gate.py approve` now requires that PASS record and writes stage-approval schema v4, fingerprinting the manual review alongside the existing technical/runtime/review evidence. Any later evidence or manual-review change makes the approval stale.

## Explicit production selection contract

`data/texture_lab/production_selection.json` starts empty and contains no automatic defaults. `oa_tex_production_selection.py` can record a `remastered` selection only after the source stage has a current manual approval receipt.

A selection is bound to:

- texture ID and source stage/preset;
- selected presentation tier (`ai_restored` or `ai_recreated`);
- candidate project-relative path and SHA-256;
- Classic source SHA-256;
- visual-review-pack manifest fingerprint;
- stage-approval receipt fingerprint;
- required manual note.

The command never copies generated pixels and never changes gameplay/runtime state. `status` revalidates candidate/source hashes, the review pack and the stage receipt; any changed evidence makes the production record `STALE`. `revoke` removes the active selection while keeping an audit record.

This preserves the distinction:

**stage approval** = the experiment may progress to the next stage;  
**production selection** = a human explicitly selected one reviewed candidate for the Remastered presentation profile.

## Structural-drift baseline

The 36 alpha-safe deterministic candidates established the first reference envelope for a layout-preserving transformation. These values are retained as historical calibration evidence; before any real AI run, RT-POC-01 now requires a fresh schema-v2 recalibration under the pinned Pillow 12.3.0 toolchain:

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

`tests/test_texture_lab_rt_poc_01.py` uses synthetic fixtures and checks scan/alpha behavior, deterministic byte-identical upscale output, pinned Pillow consistency, expected dimensions, legacy color-key safety, AI alpha-mask reapplication, staged preset selection, approval-gate prerequisites, atlas split/stitch identity, technical/structural QA planning, Qwen workflow contracts and tile-preview dimensions. GitHub Actions executes the pinned source-safe suite on Python 3.11 and 3.12 and runs the Godot Texture Lab source-contract validator.

## Next execution step

1. bootstrap/doctor the pinned Real-ESRGAN v0.3.0 + x4plus runtime on the development machine;
2. run the pinned checkpoint on the 11 AI-Restored-eligible textures;
3. run `oa_tex_structural_drift.py` and compare AI Restored results with the mathematical baseline;
4. export a fixed-seed API-format ComfyUI workflow for the selected image-edit model and run AI Recreated;
5. apply the same structural, color-key, seam and text/mask review;
6. compare Classic / Enhanced / AI Restored / AI Recreated using identical source IDs;
7. execute the dedicated Godot Texture Lab scene on the development machine before production-wide conversion.

RT-POC-01 remains observational: it does not replace Classic evidence or automatically select a production winner.
