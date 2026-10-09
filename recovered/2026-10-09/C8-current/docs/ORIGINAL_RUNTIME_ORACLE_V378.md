# OpenAzrael C8 v378 — Original DOSBox-X ↔ Godot image oracle

**Evidence state:** `SCOPED_ORIGINAL_INTRO_FRAMEBUFFER_PASS_CANDIDATE_HOLD`.

This is not a final demo Candidate. It does not certify audio onset, fades,
camera/FOV in gameplay, Niamh dialogue, dynamic R7 transforms, or the complete
KG-001 acceptance contract.

## Authority and capture provenance

The original source remains **read-only** in ATDEMO, SHA-pinned by
`R.EXE` SHA-256
`381e4f5c61e4bb8c27f06b1944e6673bbebc39ca219cc08fb9f948da2ca37c00`.
The isolated DOSBox-X guest contains all **374** files copied recursively from
the authorized original corpus and independently checked by SHA-256; no source
file was changed. DOSBox-X 2026.10.01 SDL2 Win64 original emulator binary:
`a82adcfa7af2784566cfeff74c077cefed08505396db2948b7e6aa7d4cee0832`.

Native framebuffer capture is invoked through the DOSBox-X **Take raw
screenshot** command (menu ID 5220). It does **not** use Remote Desktop
Commander's video stream, synthetic graphics, or screen transcription. Full
source and native screenshot SHA pins are in
`data/tests/original_vga_visual_contract_v377.json`.

The original engine has also reached R1 using the complete original guest.
Source-emulator R1 state was saved in DOSBox-X to
`R1_CLEAN_ORIGINAL_v374.sav` (SHA-256
`a9489051015ad06aadf68fa022ef200bd90001b707b8cd12324cea28c85eef76`),
then restored in a new emulator process to the exact same framebuffer hash.
An 8.270584 s ORIGINAL gameplay video was captured through the native
DOSBox-X AVI/ZMBV recorder; 579 frames at 640x480, PCM s16le audio, ZIPless
AVI SHA-256
`ce1bde6b0c486ef6764c00f08404578e42e44ec2efbea8b8ebc062a254c41dfb`.
Do not copy commercial binaries or extracted artwork into public source control.

## Verified original vs reconstructed rendering

Five source screenshot identity checks passed across original screenshot,
source-decoded assets, and the **rendered Godot 4.7.2 ViewportTexture**:

| Original R.EXE native frame | Godot-rendered source stage | Equality |
|---|---|---|
| MINDLOGO frame 0 | main_mindscape_frame0 | 307200/307200 |
| INTRO frame 8 | main_ig_frame8 | 307200/307200 |
| INTRO frame 28 | main_ig_frame28 | 307200/307200 |
| INTRO frame 47 | main_ig_frame47 | 307200/307200 |
| TITLE frame 0 | source_title_before_poem | 307200/307200 |

**Aggregate: 1,536,000 matching pixels, 0 differing RGB pixels.** This is
bounded frame-parity evidence only; it does not imply temporal parity of the
full startup sequence or a gameplay fidelity PASS.

## Exact TITLE VGA DAC reconstruction

The authentic PCX has RGB8 components, but the DOS VGA DAC first
truncates them to upper 6 bits before expanding them back to RGB8 via
bit replication:

```
channel6 = channel8 >> 2
display8 = (channel6 << 2) | (channel6 >> 4)
```

The old output RGB values differed by up to 2/255. Once this conversion
was verified against the original framebuffer, the TITLE became pixel
exact. `tools/build_intro_assets_v311.py` now preserves BOTH
`TITLE/frame_0000.png` as raw PCX RGB and
`TITLE/frame_0000_vga6.png` as the authentic displayed image, with
manifest provenance for each. All derived images remain Git-ignored.

Use `godot --headless --editor --import --path CHECKOUT` after regenerating
the displayed image. Skipping the import caused a correct fail-closed Godot
resource-load failure. It is not safe to bypass this missing resource gate.

## Reproducible tests

On HomePC, with the authorized local original ATDEMO corpus and generated
assets available:

```text
python tools/test_intro_title_dac_v378.py
python tools/validate_original_vga_visual_v377.py
python tools/validate_original_vs_godot_intro_v378.py
python tools/run_original_vga_oracle_v378.py
python tools/run_c8_well_regression_v364.py
```

The v378 orchestrator regenerates assets, runs the Godot importer,
executes headless, rendered and AV tests, verifies original captures plus
original save-state and video hashes, then checks five Godot-vs-original
pixel-exact snapshots. A deliberately absent original-capture path must
fail closed; the orchestrator executes that negative test before the
positive oracle tests. It does not promote the Candidate.

**Still HOLD:** timing of startup palette fades, original movement/camera
tracking in R1/R7, origin-vs-Godot visual gameplay frame diffs, Niamh
and R7 pipe event timing, audio latency/Miles parity, save/load fidelity
across original engine formats, public release safety and G10 gates.