# OpenAzrael Texture Lab — RT-POC-01

**Status:** IMPLEMENTED ON FEATURE BRANCH / RUNTIME-ASSET EXECUTION PENDING  
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

```bash
python tools/texture_lab/oa_tex_scan.py
```

### `oa_tex_enhance.py`

Creates deterministic 4x candidates using Pillow nearest, bicubic and Lanczos resampling. An external xBRZ executable can be integrated by an explicitly pinned command template; it is intentionally not assumed to exist.

```bash
python tools/texture_lab/oa_tex_enhance.py --factor 4
```

A small POC selection can be processed with:

```bash
python tools/texture_lab/oa_tex_enhance.py --only TEX_0001 TEX_0002
```

### `oa_tex_validate.py`

Checks target dimensions and records observational fidelity metrics: Lanczos round-trip MAE, optional SSIM when scikit-image is available, mean-channel drift and raw edge-seam MAE.

No automatic fidelity winner is selected in RT-POC-01. Thresholds are deliberately `UNCALIBRATED_HOLD` until representative R1/R7/R8 candidates are reviewed.

```bash
python tools/texture_lab/oa_tex_validate.py --variant lanczos_x4.png
```

### `oa_tex_compare.py`

Creates a local visual comparison sheet across Classic, mathematical Enhanced, AI Restored and AI Recreated variants.

### `oa_tex_restore.py`

A command-template adapter for a locally installed Real-ESRGAN implementation. The exact executable/model version must be pinned in the run record before a result can be considered reproducible.

### `oa_tex_recreate.py`

Generic ComfyUI API runner. It consumes an **API-format** exported workflow and patches explicit Load Image / prompt / seed nodes supplied on the command line. This keeps the repository independent of any one Qwen/FLUX graph while preserving the exact submitted workflow in each job record.

The current intended bake-off is Qwen Image Edit as the primary image-conditioned reconstruction path and FLUX Kontext as a secondary comparison path. Model licensing and exact checkpoints remain external deployment concerns and must be recorded before production adoption.

## Repository safety

The following stay out of Git:

- Classic decoded PNGs;
- mathematical Enhanced pixels;
- Real-ESRGAN outputs;
- generative AI outputs;
- comparison sheets.

Metadata-only manifests/reports may be committed after review when they contain no recoverable commercial image payload.

## RT-POC-01 test policy

`tests/test_texture_lab_rt_poc_01.py` creates a synthetic RGBA fixture and checks:

- source scanning;
- alpha detection;
- deterministic byte-identical Pillow upscales across two runs;
- expected 4x dimensions;
- stable metric helpers.

This source-safe test does not claim visual quality or original-renderer parity.

## Next execution step

On the development machine with the ignored v44 Classic texture corpus restored:

1. scan all 86 textures;
2. select ~12 representative R1/R7/R8 textures;
3. generate nearest/bicubic/Lanczos candidates;
4. pin and add xBRZ if desired;
5. run validation and visual comparison;
6. calibrate material/tileability metadata;
7. run a Real-ESRGAN bake-off;
8. export two ComfyUI API workflows (Qwen / FLUX) and run constrained AI Recreated candidates;
9. inspect candidates in a dedicated Godot Texture Lab scene before any production-wide conversion.

RT-POC-01 must remain observational: it does not replace Classic evidence or promote a visual candidate automatically.
