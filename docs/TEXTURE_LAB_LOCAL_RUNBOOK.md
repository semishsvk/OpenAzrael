# OpenAzrael Texture Lab — Local RT-POC-01 Runbook

This runbook executes the already-defined experiment. It does not change Classic evidence or promote any generated asset automatically.

## Recommended first-run launchpad

For the first real Real-ESRGAN experiment, prefer the cross-platform launchpad:

```bash
python tools/texture_lab/oa_tex_first_run.py status
```

It reports exactly which source-side prerequisites are missing without generating pixels. Source readiness requires not only 86 Classic PNGs, but also all 12 canonical RT-POC-01 texture IDs at their expected original dimensions.

If the deterministic baseline needs rebuilding:

```bash
python tools/texture_lab/oa_tex_first_run.py prepare-baseline
```

To create/download the pinned Real-ESRGAN source, checkpoint and isolated **Python 3.11** venv, point the launchpad at a Python 3.11 interpreter:

```bash
python tools/texture_lab/oa_tex_first_run.py bootstrap-realesrgan \
  --runtime-python <PYTHON_3_11>
```

The source-safe tooling may still run under the CI-supported Python 3.11/3.12 matrix; the AI runtime is a separate environment.

RT-POC-01 pins the compatibility pair **torch 2.1.2 + torchvision 0.16.2**. Choose only the official PyTorch wheel index appropriate for the development machine. For example:

```bash
<REAL_ESRGAN_VENV_PYTHON> -m pip install \
  torch==2.1.2 torchvision==0.16.2 \
  --index-url https://download.pytorch.org/whl/cu121
```

Use `cu118` or `cpu` instead of `cu121` when that is the correct official backend for the machine. The CUDA/CPU index remains machine-specific; the torch/torchvision versions do not.

Verify the exact compatibility contract:

```bash
python tools/texture_lab/oa_tex_realesrgan_runtime.py check \
  --python-exe <REAL_ESRGAN_VENV_PYTHON>
```

Only then request the remaining texture-only Real-ESRGAN Python dependencies:

```bash
python tools/texture_lab/oa_tex_first_run.py bootstrap-realesrgan \
  --install-python-deps
```

The bootstrap installs exact `basicsr==1.4.2` and the pinned Real-ESRGAN source as editable `--no-deps`. GFPGAN/facexlib are deliberately excluded because RT-POC-01 never enables face enhancement. The runtime doctor rechecks Python/Torch/torchvision/BasicSR compatibility and fingerprints the installed pip environment before inference.

Once `status` is source-ready, run the final **non-generating readiness gate**:

```bash
python tools/texture_lab/oa_tex_first_run.py check-restored-smoke-1
```

This performs, in order:

1. the exact Python 3.11 / torch / torchvision / BasicSR / Real-ESRGAN runtime-contract probe;
2. the canonical `restored_smoke_1` local preflight;
3. the pinned Real-ESRGAN doctor;
4. a canonical `restored_smoke_1` bake-off **dry-run**.

It writes readiness evidence under `.local/texture_lab/launchpad/`, but does not run inference, approve anything or clear a named-stage run/candidate namespace. Treat **PASS** here as `RUNTIME_READY_FOR_REAL_SMOKE`, not as evidence that any AI pixel has been generated.

Only after that passes, execute the first canonical experiment:

```bash
python tools/texture_lab/oa_tex_first_run.py restored-smoke-1
```

That command runs the local preflight, the pinned Real-ESRGAN doctor, and then the real canonical `restored_smoke_1` bake-off. It stops on the first failing gate and writes launch evidence under `.local/texture_lab/launchpad/`. The staged bake-off writes canonical run evidence under `.local/texture_lab/runs/rt_poc_01/restored_smoke_1/` and the generated CORIROCK candidate under the preset-scoped ignored asset namespace.

If that exact preset already has local run/candidate artifacts and you intentionally want to start it again from a clean slate, stay on the high-level launchpad and make the destructive intent explicit:

```bash
python tools/texture_lab/oa_tex_first_run.py restored-smoke-1 \
  --replace-existing-run
```

The non-generating `check-restored-smoke-1` command refuses `--replace-existing-run`; readiness checks therefore never clear stage data.

After any real `restored_smoke_1` attempt, inspect the passive state machine:

```bash
python tools/texture_lab/oa_tex_first_run.py restored-smoke-1-status
```

It never creates review decisions or approvals. It reports one of:

- `NOT_EXECUTED`
- `EVIDENCE_HOLD`
- `READY_FOR_MANUAL_REVIEW`
- `MANUAL_REVIEW_IN_PROGRESS`
- `MANUAL_REVIEW_STALE`
- `READY_FOR_STAGE_APPROVAL`
- `APPROVAL_STALE`
- `STAGE_APPROVED`

and includes the exact next action. `STAGE_APPROVED` still does **not** imply production selection.

A successful named stage also writes:

`.local/texture_lab/runs/rt_poc_01/restored_smoke_1/review_handoff.html`

The HTML handoff embeds/links the full comparison sheet, detail comparison, alpha evidence sheet, repeat-tile preview when applicable, review attention, required manual checks and the Godot REVIEW instructions. It is explicitly observational and is **not** included as approval evidence; authoritative approval remains the structured manual-review record plus approval v5 chain.

Use the lower-level commands in the rest of this runbook for diagnosis or controlled reruns.

## Review Pack 01 — prioritized human review

Review Pack 01 is a source-safe planning layer over the same 12 canonical POC textures. It does not add a new AI stage or bypass stage approval.

Validate it at any time:

```bash
python tools/texture_lab/oa_tex_review_pack_01.py validate
```

Render the current deterministic source plan:

```bash
python tools/texture_lab/oa_tex_review_pack_01.py render \
  --out-json .local/texture_lab/review_pack_01/source_plan.json \
  --out-md .local/texture_lab/review_pack_01/source_plan.md
```

The source plan groups textures into P1/P2/P3 human-review order and into three treatment classes:

- `safe_upscale`
- `ai_recreation_candidate`
- `conservative`

It derives actual AI eligibility and the earliest named Restored/Recreated stage from the existing canonical policy/smoke contracts. For example, KEYHOLE# remains Classic + Enhanced-nearest only; BAPTAP's first Recreated evidence comes from `recreated_atlas`.

To inspect what is actually available on the local machine without generating or approving anything:

```bash
python tools/texture_lab/oa_tex_review_pack_01.py status \
  --out-json .local/texture_lab/review_pack_01/availability.json \
  --out-md .local/texture_lab/review_pack_01/availability.md
```

The dashboard reports Classic/Enhanced reference availability and current named-stage AI evidence. `REFERENCE_ONLY_AI_NOT_CURRENT` is informational, not a failure or quality judgment. `READY_WITH_CURRENT_AI_EVIDENCE` means only that valid current AI stage evidence exists and can be reviewed.

For a single per-asset lifecycle/readiness view, build the passive asset-status dashboard:

```bash
python tools/texture_lab/oa_tex_asset_status.py
```

It writes `.local/texture_lab/asset_status.json` and `.local/texture_lab/asset_status.md`. The dashboard combines the canonical review plan, local Classic/Enhanced presence, current named-stage AI evidence, optional transparency scan metadata, and explicit production-selection validity. It never ranks candidates, infers visual quality, or promotes a texture.

To materialize the prioritized local full/detail visual overview from whatever current evidence is actually available:

```bash
python tools/texture_lab/oa_tex_review_pack_01.py hub \
  --out-dir .local/texture_lab/review_pack_01/current
```

The hub refuses stale file fingerprints and never becomes approval evidence. Stage-specific tile/seam imagery and structured manual review remain authoritative.

See `docs/TEXTURE_LAB_REVIEW_PACK_01.md` for the complete order and eight-axis manual rubric. No aggregate score or automatic winner is computed.

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

Install **torch 2.1.2 + torchvision 0.16.2** into that venv from the appropriate official PyTorch `cu118`, `cu121` or `cpu` index. Do not substitute torchvision 0.17+: BasicSR 1.4.2 relies on the older `torchvision.transforms.functional_tensor` compatibility surface.

Then install the minimal pinned texture runtime into the same venv:

```bash
python tools/texture_lab/oa_tex_realesrgan_bootstrap.py \
  --install-python-deps \
  --python-exe <REAL_ESRGAN_VENV_PYTHON>
```

This installs `basicsr==1.4.2` and the pinned Real-ESRGAN source with `--no-deps`; the face-enhancement-only GFPGAN/facexlib stack is intentionally absent.

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

Review the generated stage handoff first:

`.local/texture_lab/runs/rt_poc_01/restored_smoke_1/run_summary.md`

It points to the stage's full comparison, deterministic detail comparison and any repeat-sampling tile preview. The lower-level queue remains available at:

`.local/texture_lab/runs/rt_poc_01/restored_smoke_1/ai_restored_review_queue.md`

After the PNG/Godot inspection, initialize the structured manual review:

```bash
python tools/texture_lab/oa_tex_manual_review.py init restored_smoke_1
```

For each texture, record the final human decision and every required check. For example, inspect the generated review record to see the exact required check names, then record them:

```bash
python tools/texture_lab/oa_tex_manual_review.py record restored_smoke_1 CORIROCK \
  --decision ACCEPTED_FOR_STAGE \
  --check composition_geometry_preserved=true \
  --check no_invented_objects_symbols_or_text=true \
  --check material_detail_plausible=true \
  --check detail_artifacts_acceptable=true \
  --check alpha_mask_boundaries_acceptable=true \
  --check gameplay_scale_acceptable=true \
  --note "manual full/detail/Godot A/B review completed"
```

The exact required check list may contain additional seam/text/artwork/geometry/atlas checks depending on the texture policy. An accepted texture requires every required check to be `true`.

Confirm the whole stage review is complete:

```bash
python tools/texture_lab/oa_tex_manual_review.py status restored_smoke_1
```

Only after that returns PASS may the stage be approved:

```bash
python tools/texture_lab/oa_tex_stage_gate.py approve restored_smoke_1 \
  --note "structured manual review PASS"
```

After `restored_smoke_1` is fully reviewed and its stage approval is current, capture the exact working Real-ESRGAN environment as a **local lock candidate**:

```bash
python tools/texture_lab/oa_tex_realesrgan_lock.py restored_smoke_1
```

This requires the current approval v5 receipt, rereads the approved `realesrgan_doctor.json`, and writes only local candidate artifacts under `.local/texture_lab/runtime_locks/`:

- `realesrgan_rt_poc_01_candidate.json` — Python/platform/Torch/CUDA/GPU, pinned source/checkpoint identity, runtime probe and full pip-freeze fingerprint;
- `realesrgan_rt_poc_01_requirements.txt` — exact normalized pip-freeze package set.

The tool has `automatic_promotion=false` and does **not** mutate `realesrgan_runtime_contract.json` or any canonical repository lock. Treat the result as the evidence-backed candidate for a later explicit repository promotion after human inspection.

To render the exact proposed repository lock **without mutating tracked files**, run:

```bash
python tools/texture_lab/oa_tex_realesrgan_lock_plan.py
```

This compares the local approved runtime candidate against the provisional runtime contract and, on PASS, writes only under:

`.local/texture_lab/runtime_locks/promotion_plan/`

The proposal contains:

- `promotion_plan.json` with compatibility checks and SHA-256 values for every proposed tracked file;
- proposed `realesrgan_environment_lock.json`;
- proposed `requirements-realesrgan-lock.txt`.

The plan state is `READY_FOR_HUMAN_PROMOTION_REVIEW`. It carries `automatic_promotion=false` and `canonical_files_mutated=false`. The canonical repository lock must still be promoted by a separate explicit repository change after reviewing the candidate and proposed files.

Only then proceed to `restored_smoke_4`. Review it and approve it the same way before `restored_full`.

The next preset begins with a stage-gate check. An approval v5 receipt is bound to the exact plan, unique `run_instance_id`, local preflight, backend doctor/preflight, technical validation, structural-drift report, generation provenance, review queue, review pack, output SHA-256 values and structured manual review.

A named preset is a clean-run namespace. If its run evidence or preset-scoped candidate directory already contains artifacts, a real rerun is refused by default. After reviewing/backing up the old local evidence, an intentional clean rerun must use:

```bash
python tools/texture_lab/oa_tex_ai_bakeoff.py restored \
  --preset restored_smoke_1 \
  --replace-existing-run \
  --realesrgan-python <REAL_ESRGAN_VENV_PYTHON> \
  --realesrgan-root .local/texture_lab/realesrgan/Real-ESRGAN \
  --model-path .local/texture_lab/realesrgan/weights/RealESRGAN_x4plus.pth
```

That flag deletes only the selected preset's local run evidence and preset-scoped generated candidates before starting clean. Every real named rerun receives a fresh `run_instance_id`, so an older manual review/approval cannot become current again merely because regenerated pixels happen to be byte-identical.

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

The high-level launchpad mirrors the Restored CHECK → RUN → STATUS flow.

Final **non-generating** readiness gate:

```bash
python tools/texture_lab/oa_tex_first_run.py check-recreated-smoke-1 \
  --comfy-root <COMFYUI_ROOT>
```

This executes, in order:

1. canonical local preflight for `recreated_smoke_1`;
2. live ComfyUI node/input contract doctor;
3. exact Qwen workflow/model-file preflight with pinned SHA-256 identities;
4. canonical Recreated bake-off dry-run.

It does not submit a Qwen job and refuses `--replace-existing-run`.

Only after PASS, run the real first Recreated smoke:

```bash
python tools/texture_lab/oa_tex_first_run.py recreated-smoke-1 \
  --comfy-root <COMFYUI_ROOT>
```

For an intentional clean rerun of that same stage:

```bash
python tools/texture_lab/oa_tex_first_run.py recreated-smoke-1 \
  --comfy-root <COMFYUI_ROOT> \
  --replace-existing-run
```

After any real attempt, inspect the passive state machine:

```bash
python tools/texture_lab/oa_tex_first_run.py recreated-smoke-1-status
```

It reports the same review/approval lifecycle used by Restored and never initializes, records or approves anything. `STAGE_APPROVED` only unlocks `recreated_smoke_4`; production selection remains separate.

The lower-level equivalent remains available for diagnosis:

```bash
python tools/texture_lab/oa_tex_ai_bakeoff.py recreated \
  --preset recreated_smoke_1 \
  --comfy-root <COMFYUI_ROOT>
```

After reviewing `recreated_smoke_1`, run the same structured review contract used by Restored:

```bash
python tools/texture_lab/oa_tex_manual_review.py init recreated_smoke_1
```

Record every texture with all policy-derived required checks, then require:

```bash
python tools/texture_lab/oa_tex_manual_review.py status recreated_smoke_1
```

Only after that returns PASS:

```bash
python tools/texture_lab/oa_tex_stage_gate.py approve recreated_smoke_1 \
  --note "structured manual review PASS"
```

After the approval is current, capture the exact working ComfyUI/Qwen runtime provenance:

```bash
python tools/texture_lab/oa_tex_qwen_lock.py recreated_smoke_1
```

This writes only the local candidate:

`.local/texture_lab/runtime_locks/qwen_2511_rt_poc_01_candidate.json`

It captures the ComfyUI/Python/PyTorch/device system identity, node contract, canonical workflow SHA/bindings, pinned model-file identities, fixed sampling evidence and approved Qwen job records. It carries `automatic_promotion=false` and does not change repository config.

To render the proposed repository environment lock without mutating tracked files:

```bash
python tools/texture_lab/oa_tex_qwen_lock_plan.py
```

The local proposal under `.local/texture_lab/runtime_locks/qwen_promotion_plan/` is `READY_FOR_HUMAN_PROMOTION_REVIEW` only when the candidate still matches the canonical workflow, model hashes/sizes, seed and model label. The final `qwen_environment_lock.json` remains a separate explicit repository promotion.

Then proceed through the gated sequence:

- `recreated_smoke_4` — requires approved `recreated_smoke_1`;
- `recreated_atlas` — requires approved `recreated_smoke_4`;
- `recreated_full` — requires current approvals for both `recreated_smoke_4` and `recreated_atlas`.

Each named preset has an isolated evidence directory under `.local/texture_lab/runs/rt_poc_01/<preset>/` and a preset-scoped candidate namespace under `assets/textures/ai_restored/_runs/<preset>/` or `assets/textures/ai_recreated/_runs/<preset>/`. A different preset therefore cannot overwrite an earlier stage's reviewed candidates. Re-running the same preset intentionally replaces that preset's candidate/evidence and makes any older review/approval stale. A `--dry-run` plan is written under `.local/texture_lab/runs/rt_poc_01/_dry_run_plans/` so it cannot overwrite an approved real-run plan.

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
- O — switch profile source between current stage REVIEW and REMASTERED production profile;
- P — reload/toggle the selected profile source;
- S — local screenshot.

The Texture Lab scene does not mutate gameplay state.

## Cross-tier production review

When the same texture has current approved candidates from both Restored and Recreated, build the recommended four-tier review bundle before choosing a production default:

```bash
python tools/texture_lab/oa_tex_production_review.py CORIROCK \
  --restored-preset restored_smoke_1 \
  --recreated-preset recreated_smoke_1
```

The output lives under:

`.local/texture_lab/production_review/CORIROCK/restored_smoke_1__recreated_smoke_1/`

and contains:

- Classic → Enhanced Lanczos → AI Restored → AI Recreated full comparison;
- normalized four-tier detail crops;
- separate 3×3 Restored/Recreated repeat previews when repeat sampling applies;
- SHA-256 fingerprints for every input/output;
- current approval provenance;
- explicit human review questions and allowed manual outcomes.

The bundle schema is `openazrael.texture_lab.production_review_bundle.v1`. It carries both `automatic_selection=false` and `automatic_quality_verdict=false`. It never ranks Restored versus Recreated and never writes `production_selection.json`.

This comparison is recommended whenever both AI modes are valid for a texture. It is not a mandatory gate for textures whose policy permits only one AI mode or deliberately prefers Classic/Enhanced.

## Production selection registry

A successful stage approval still does **not** make its textures production defaults.

After a candidate has separately passed the intended manual production review, record that explicit choice with:

```bash
python tools/texture_lab/oa_tex_production_selection.py select CORIROCK \
  --preset restored_smoke_1 \
  --note "manual production selection after full/detail/Godot A/B review"
```

Check all current selections with:

```bash
python tools/texture_lab/oa_tex_production_selection.py status
```

If candidate pixels, the Classic source, the review pack or the underlying stage approval change, status becomes `STALE`.

To withdraw a selection without deleting its audit history:

```bash
python tools/texture_lab/oa_tex_production_selection.py revoke CORIROCK \
  --note "selection withdrawn after later comparison"
```

The registry records metadata only; it does not copy pixels or alter the game. Registry schema v2 preserves `superseded_selections` and `revocations` as append-only audit history. A legacy v1 registry is migrated in memory to v2 when loaded; the next explicit mutation writes the v2 contract.

## Runtime profile manifests

Generate local presentation manifests after or independently of production selection:

```bash
python tools/texture_lab/oa_tex_runtime_manifest.py classic
python tools/texture_lab/oa_tex_runtime_manifest.py enhanced --enhanced-method lanczos
python tools/texture_lab/oa_tex_runtime_manifest.py remastered
```

They are written under:

`.local/texture_lab/runtime_manifests/`

For an export/readiness check, use strict Remastered validation:

```bash
python tools/texture_lab/oa_tex_runtime_manifest.py remastered --strict
```

Remastered never consumes an unapproved AI file. A current explicit production selection resolves to that exact candidate; no selection falls back to Classic; a stale selection also falls back to Classic and is reported as stale. Missing resolved files remain a HOLD.

After generating `remastered.json`, launch the isolated Godot Texture Lab, press **O** to select REMASTERED and **P** to reload/toggle it. Named AI stages automatically also write `<run_dir>/godot_review_profile.json` plus the convenience pointer `.local/texture_lab/runtime_manifests/review_current.json`; select REVIEW with **O** and toggle it with **P** during stage QA. The stage-specific copy is audit evidence, while `review_current.json` is only a replaceable convenience pointer.

The Godot profile resolver reads only the resolved manifest. It does not read stage evidence or `production_selection.json` directly.

## Pre-export texture integrity

After generating a runtime profile manifest, verify it before any export/build handoff:

```bash
python tools/texture_lab/oa_tex_runtime_verify.py \
  .local/texture_lab/runtime_manifests/remastered.json
```

Only a PASS manifest may be compiled into the static Godot runtime map:

```bash
python tools/texture_lab/oa_tex_runtime_export.py \
  .local/texture_lab/runtime_manifests/remastered.json
```

The export compiler writes only local metadata/code under `.local/texture_lab/runtime_export/`. It does not copy texture pixels. If any resolved PNG, selection/policy input or production registry changes, regenerate and reverify the runtime manifest.

The exported-game loader contract uses `ResourceLoader` for imported `Texture2D` assets. The editor-only profile preview additionally verifies raw source hashes before displaying a manifest.

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


## Godot A/B inspection

In the isolated Texture Lab scene, press **B** to toggle side-by-side A/B mode. Keys **1–4** choose the candidate tier and **R** cycles the reference tier. Both surfaces share the same tiling and lighting state. This allows Classic vs Enhanced/Restored/Recreated as well as Restored vs Recreated comparisons without touching gameplay state.

The generated visual review pack also includes a deterministic detail sheet using the same upper-left, center and lower-right normalized regions across Classic, Enhanced and AI candidates. Use the full sheet for composition and the detail sheet for microdetail/artifact inspection.
