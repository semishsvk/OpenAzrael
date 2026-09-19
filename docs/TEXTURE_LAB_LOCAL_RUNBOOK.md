# OpenAzrael Texture Lab — Local RT-POC-01 Runbook

This runbook executes the already-defined experiment. It does not change Classic evidence or promote any generated asset automatically.

## 0. Preconditions

Use the `texture-lab-rt-poc-01` branch.

The local ignored corpus must exist:

- `assets/textures/classic/` — 86 decoded Classic PNGs;
- `assets/rooms/R1.glb`, `R7.glb`, `R8.glb`;
- v44 manifests under `data/`.

Generated assets and model runtimes live outside normal Git history.

### Local readiness preflight

Before a real AI stage, run the stage-aware local preflight. It checks the 86-texture Classic corpus, required Enhanced conditioning inputs, available disk space, model-file presence/size planning, RAM/GPU visibility and the backend paths supplied on the command line. RAM/VRAM are reported, not used as arbitrary hard acceptance thresholds; the backend doctors remain authoritative.

For the first Restored smoke:

```bash
python tools/texture_lab/oa_tex_local_preflight.py \
  --preset restored_smoke_1 \
  --realesrgan-root .local/texture_lab/realesrgan/Real-ESRGAN \
  --model-path .local/texture_lab/realesrgan/weights/RealESRGAN_x4plus.pth \
  --realesrgan-python <REAL_ESRGAN_VENV_PYTHON>
```

For the first Recreated smoke:

```bash
python tools/texture_lab/oa_tex_local_preflight.py \
  --preset recreated_smoke_1 \
  --comfy-root <COMFYUI_ROOT>
```

For Qwen, missing model files are translated into an exact required-byte total plus a 5 GiB disk safety margin. Exact SHA-256 verification still happens in `oa_tex_qwen_preflight.py`.

## 1. Rebuild deterministic Enhanced baseline

Install the pinned source-safe image toolchain first:

```bash
python -m pip install -r tools/texture_lab/requirements-source-safe.txt
```

RT-POC-01 currently pins Pillow **12.3.0**. The mathematical bake-off and drift calibration refuse to run under a different Pillow version so that the Enhanced reference is not silently changed by a library upgrade.

Rebuild the Enhanced candidates and then recalibrate the deterministic structural envelope:

```bash
python tools/texture_lab/oa_tex_scan.py
python tools/texture_lab/oa_tex_run_poc.py
python tools/texture_lab/oa_tex_calibrate_drift.py
```

The new `data/texture_lab/rt_poc_01_drift_baseline.json` records the Pillow and Python toolchain used for calibration. The local AI preflight requires the baseline's Pillow version to match the pinned source-safe version.

The canonical Qwen conditioning variant for RT-POC-01 is `lanczos_x4.png`, except assets excluded by AI policy.

## 2. Prepare isolated Real-ESRGAN runtime

Create the pinned source/model runtime and a local Python venv:

```bash
python tools/texture_lab/oa_tex_realesrgan_bootstrap.py \
  --clone-upstream \
  --download-model \
  --create-venv
```

Venv Python:

- Windows: `.local\texture_lab\realesrgan\venv\Scripts\python.exe`
- Linux/macOS: `.local/texture_lab/realesrgan/venv/bin/python`

Install the PyTorch build appropriate for the machine/GPU into that venv first. Do not hard-code a CUDA wheel in the repository.

Then install the pinned Real-ESRGAN Python dependencies into the same venv:

```bash
python tools/texture_lab/oa_tex_realesrgan_bootstrap.py \
  --install-python-deps \
  --python-exe <REAL_ESRGAN_VENV_PYTHON>
```

The doctor must pass before generation:

```bash
<REAL_ESRGAN_VENV_PYTHON> tools/texture_lab/oa_tex_realesrgan_doctor.py \
  --realesrgan-root .local/texture_lab/realesrgan/Real-ESRGAN \
  --model-path .local/texture_lab/realesrgan/weights/RealESRGAN_x4plus.pth
```

## 3. AI Restored staged execution

Start with one texture:

```bash
python tools/texture_lab/oa_tex_ai_bakeoff.py restored \
  --preset restored_smoke_1 \
  --realesrgan-python <REAL_ESRGAN_VENV_PYTHON> \
  --realesrgan-root .local/texture_lab/realesrgan/Real-ESRGAN \
  --model-path .local/texture_lab/realesrgan/weights/RealESRGAN_x4plus.pth
```

Review the generated queue under the preset-specific evidence directory:

`.local/texture_lab/runs/rt_poc_01/restored_smoke_1/ai_restored_review_queue.md`

After manual PNG/Godot review, explicitly approve the stage:

```bash
python tools/texture_lab/oa_tex_stage_gate.py approve restored_smoke_1 \
  --note "manual visual/QA review completed"
```

Only then run `restored_smoke_4`. Review it and approve it the same way before `restored_full`.

The next preset begins with a stage-gate check. An approval receipt is bound to the exact plan, local preflight, backend doctor/preflight, technical validation, structural-drift report, generation/job records, review queue and output SHA-256 values. Re-running a previously approved stage with changed evidence makes its receipt stale and requires a new manual approval.

## 4. Prepare Qwen / ComfyUI

Use a current ComfyUI installation exposing the local HTTP API (default `127.0.0.1:8188`).

The exact RT-POC-01 model identities and paths are in:

`tools/texture_lab/config/qwen_2511_contract.json`

Required model locations inside the ComfyUI root:

- `models/diffusion_models/qwen_image_edit_2511_fp8mixed.safetensors`
- `models/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors`
- `models/vae/qwen_image_vae.safetensors`

Plan the model installation first; this performs no network download:

```bash
python tools/texture_lab/oa_tex_qwen_bootstrap.py \
  --comfy-root <COMFYUI_ROOT>
```

Then download missing models from the pinned HTTPS sources:

```bash
python tools/texture_lab/oa_tex_qwen_bootstrap.py \
  --comfy-root <COMFYUI_ROOT> \
  --download
```

Downloads use `.partial` files and HTTP Range when available, so an interrupted multi-GB transfer can resume. A server that ignores Range causes a safe restart instead of an append/corruption. The final filename is created only after exact size and SHA-256 verification. An existing invalid final file is never overwritten unless `--replace-invalid` is explicitly supplied. Public model files need no token; if the host requires authentication, the bootstrap reads `HF_TOKEN` by default without storing it in Git or the report.

The bootstrap verifies model-file identity, but it does **not** replace the independent runtime/workflow preflight below. The optional Lightning LoRA remains deliberately disabled for calibration.

With ComfyUI running:

```bash
python tools/texture_lab/oa_tex_comfy_doctor.py
```

Then verify the canonical repository workflow and model files:

```bash
python tools/texture_lab/oa_tex_qwen_preflight.py \
  tools/texture_lab/workflows/qwen_2511_openazrael_api.json \
  --comfy-root <COMFYUI_ROOT> \
  --require-model-files
```

Both commands must PASS before a real Recreated run.

## 5. AI Recreated staged execution

First smoke:

```bash
python tools/texture_lab/oa_tex_ai_bakeoff.py recreated \
  --preset recreated_smoke_1 \
  --comfy-root <COMFYUI_ROOT>
```

After reviewing `recreated_smoke_1`, approve it explicitly:

```bash
python tools/texture_lab/oa_tex_stage_gate.py approve recreated_smoke_1 \
  --note "manual visual/QA review completed"
```

Then proceed through the gated sequence:

- `recreated_smoke_4` — requires approved `recreated_smoke_1`;
- `recreated_atlas` — requires approved `recreated_smoke_4`;
- `recreated_full` — requires current approvals for both `recreated_smoke_4` and `recreated_atlas`.

Each named preset has an isolated evidence directory under `.local/texture_lab/runs/rt_poc_01/<preset>/`. Review queues therefore cannot accidentally inherit stale results from another stage. A `--dry-run` plan is written under `.local/texture_lab/runs/rt_poc_01/_dry_run_plans/` so it cannot overwrite an approved real-run plan.

The canonical graph uses:

- fixed seed 734234;
- 40 steps;
- CFG 4.0;
- Euler sampler;
- simple scheduler;
- no Lightning LoRA;
- separate positive and negative Qwen conditioning;
- 4x Enhanced canvas as AI input;
- Classic as structural/alpha truth.

## 6. Special assets

### KEYHOLE#

No AI processing. Keep deterministic Enhanced/nearest.

### SHIELD1

AI Restored is allowed. AI Recreated is disabled by default because the original lettering must not be rewritten.

### BAPFLOR#

Requires exact Classic-derived alpha lock and U/V seam review.

### BAPTAP

The atlas is never generated as one panorama.

Pipeline:

`Classic/Enhanced atlas -> 4 exact U quarters -> Qwen per quarter -> exact stitch -> full-atlas QA`

Measured R8 UV evidence for the four quarters is stored in `data/texture_lab/rt_poc_01_sampling_review.json`.

## 7. Godot visual inspection

After candidate images exist, run the isolated test scene:

```bash
godot --path . res://tools/texture_lab/godot/texture_lab.tscn
```

Controls:

- Left / Right — texture;
- 1 / 2 / 3 / 4 — Classic / Enhanced / AI Restored / AI Recreated;
- Q / W / E — nearest / bicubic / Lanczos;
- T — 1x1 / 2x2 / 4x4 repeat;
- L — unshaded / directional light;
- S — local screenshot.

The Texture Lab scene does not mutate gameplay state.

## 8. Promotion rule

No numerical metric or completed command promotes an asset automatically.

A candidate can become a production default only after:

1. pinned-toolchain local preflight;
2. backend runtime doctor/preflight;
3. technical validation;
4. structural-drift review;
5. alpha/seam/atlas/text/puzzle checks required by its policy;
6. visual inspection in the Godot Texture Lab;
7. explicit stage approval receipt for staged execution;
8. explicit production selection.

Stage approval is intentionally separate from production promotion: an approved smoke stage only permits the next experiment stage. It does not make its generated textures production defaults.

Until then, Classic remains the evidence source and generated variants remain observational.


## Source-relative seam review

Technical QA records the Classic edge seam and the generated candidate edge seam separately. The review queue shows the candidate-minus-Classic delta for U and V. A positive delta means the generated candidate has a larger edge discontinuity than the Classic source on that axis; a negative delta means the measured edge discontinuity is smaller. These values are observational and must be interpreted together with the 3x3 visual tile preview rather than used as an automatic quality verdict.

Comparison sheets preserve original aspect ratio and show transparent pixels over a checkerboard. Do not judge geometry from older square-stretched comparison images.
