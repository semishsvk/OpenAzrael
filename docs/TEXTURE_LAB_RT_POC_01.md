# OpenAzrael Texture Lab — RT-POC-01

**Status:** SOURCE-SAFE TOOLING TESTED / REAL MATHEMATICAL BAKE-OFF EXECUTED / GODOT LAB SOURCE-READY / AI BAKE-OFF PENDING  
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
Checks target dimensions and records observational fidelity metrics: Lanczos round-trip MAE, optional SSIM when scikit-image is available, mean-channel drift and raw edge-seam MAE. Missing candidates are technical failures.

### `oa_tex_compare.py`
Creates a local visual comparison sheet across Classic, mathematical Enhanced, AI Restored and AI Recreated variants.

### `oa_tex_tile.py`
Creates a 3x3 (or configurable) repeated texture preview for direct seam/tiling inspection. The image remains repository-ignored.

### `oa_tex_run_poc.py`
Runs the canonical 12-texture mathematical RT-POC-01 selection in one command and produces nearest/bicubic/Lanczos variants plus observational metrics.

```bash
python tools/texture_lab/oa_tex_run_poc.py
```

The canonical selection is stored in `config/rt_poc_01_selection.json`. It contains four R1, four R7 and four R8 textures covering rock/organic surface, architecture, parchment, hard-edge mask, carved wall, character detail, mechanism, floor, glass, high-detail mural and text/decorative content.

### `oa_tex_restore.py`
Supports a pinned official Real-ESRGAN Python backend plus a fallback command-template backend. The preferred POC path records the exact checkpoint SHA-256, tile setting, precision mode and denoise strength. `tile=0` is the default fidelity path; tiling is a resource fallback, not the baseline.

### `oa_tex_recreate.py`
Generic ComfyUI API runner. It consumes an API-format exported workflow and patches explicit Load Image / prompt / seed nodes supplied on the command line. Each job record fingerprints the workflow template, submitted workflow, source, output and explicitly supplied model files.

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

Round-trip similarity predictably favors nearest-neighbour because it preserves the original pixel lattice most directly. This is **not** treated as a visual-quality winner.\n\nA follow-up visual QA pass identified legacy `#` textures containing quantized magenta (`R/B >= 248`, `G <= 12`). RT-POC-01 now treats only `#` assets with observed magenta as conservative color-key candidates: magenta becomes alpha=0, filtered RGB uses premultiplied alpha, and the deterministic Enhanced tier restores the alpha mask with nearest-neighbour. The validator rejects visible magenta bleed and non-binary alpha for these candidates. This is a presentation-safety rule, not a claim that complete original-renderer transparency semantics are recovered. Visual inspection shows why the selection must remain content-aware: hard-edge/mask content benefits from exact edge preservation, while photographic/organic/architectural surfaces can benefit from smoother high-quality reconstruction. No global method is promoted by RT-POC-01.

## Repository safety

Classic decoded PNGs, all generated Enhanced/AI pixels and comparison/tile sheets remain outside Git. Metadata-only manifests/reports may be committed only after review.

## Test policy

`tests/test_texture_lab_rt_poc_01.py` uses a synthetic RGBA fixture and checks scan/alpha behavior, deterministic byte-identical upscale output, expected dimensions, stable metrics and tile-preview dimensions. GitHub Actions executes the source-safe suite on Python 3.11 and 3.12 and runs the Godot Texture Lab source-contract validator.

## Next execution step

1. calibrate tileability/material metadata for the 12-texture set;
2. pin a local Real-ESRGAN implementation/checkpoint and run AI Restored;
3. export API-format ComfyUI workflows for the selected image-edit models and run AI Recreated with fixed seeds;
4. compare Classic / Enhanced / AI Restored / AI Recreated using identical source IDs;
5. execute the dedicated Godot Texture Lab scene on the development machine before production-wide conversion.

RT-POC-01 remains observational: it does not replace Classic evidence or automatically select a production winner.
