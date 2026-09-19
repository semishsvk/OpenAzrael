# OpenAzrael Texture Lab — Local RT-POC-01 Runbook

This runbook executes the already-defined experiment. It does not change Classic evidence or promote any generated asset automatically.

## 0. Preconditions

Use the `texture-lab-rt-poc-01` branch.

The local ignored corpus must exist:

- `assets/textures/classic/` — 86 decoded Classic PNGs;
- `assets/rooms/R1.glb`, `R7.glb`, `R8.glb`;
- v44 manifests under `data/`.

Generated assets and model runtimes live outside normal Git history.

## 1. Rebuild deterministic Enhanced baseline

```bash
python tools/texture_lab/oa_tex_scan.py
python tools/texture_lab/oa_tex_run_poc.py
```

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

Review the generated queue under:

` .local/texture_lab/runs/rt_poc_01/ai_restored_review_queue.md `

Then run, in order:

- `restored_smoke_4`
- `restored_full`

Do not advance only because the scripts completed. Inspect the PNGs and review queue first.

## 4. Prepare Qwen / ComfyUI

Use a current ComfyUI installation exposing the local HTTP API (default `127.0.0.1:8188`).

The exact RT-POC-01 model identities and paths are in:

`tools/texture_lab/config/qwen_2511_contract.json`

Required model locations inside the ComfyUI root:

- `models/diffusion_models/qwen_image_edit_2511_fp8mixed.safetensors`
- `models/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors`
- `models/vae/qwen_image_vae.safetensors`

The preflight verifies exact byte sizes and SHA-256 hashes. The optional Lightning LoRA is deliberately disabled for calibration.

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

Then, only after visual/QA review:

- `recreated_smoke_4`
- `recreated_atlas`
- `recreated_full`

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

1. technical validation;
2. structural-drift review;
3. alpha/seam/atlas/text/puzzle checks required by its policy;
4. visual inspection in the Godot Texture Lab;
5. explicit production selection.

Until then, Classic remains the evidence source and generated variants remain observational.
