# OpenAzrael Audio Lab — AL-POC-01

## Goal

AL-POC-01 is a source-safe, read-only audio inventory and QA tool. It is deliberately isolated from the Godot runtime and from the original/commercial audio payloads.

The current recovered demo IR describes 30 WAV assets. They are all mono 8-bit PCM and use the recovered source sample rates 11025, 22050, or 22222 Hz. The Lab treats those values as evidence to verify, not as values to normalize.

The milestone contract is frozen in `data/audio_lab/al_poc_01_contract.json`.

## Source-safety invariants

- Never rewrite, normalize, resample, repair, pad, rename, or relocate source audio.
- Never modify Godot runtime/gameplay files from Audio Lab.
- Hash source files before reporting and record a deterministic source-tree digest.
- Write generated reports only to the chosen output directory (default: `.tmp/audio_lab/al_poc_01`).
- Treat malformed-but-readable legacy containers as evidence. Example: an odd terminal RIFF data chunk without a pad byte is reported, not silently fixed.
- Keep enhancement/restoration out of AL-POC-01.

## Current pipeline

1. Recursively inventory supported audio extensions.
2. SHA-256 every source asset.
3. Parse RIFF/WAVE with a tolerant read-only parser.
4. Extract PCM metadata, duration, peak, RMS, clipping indication, leading/trailing near-silence, and compact waveform bins.
5. Merge expected evidence from:
   - `data/audio/legacy_world_ir.json` (full recovered demo audio corpus)
   - `data/backup/source_fingerprints.json` (candidate source fingerprints)
6. Verify hashes and recovered PCM metadata.
7. Discover literal repository references and classify runtime mappings.
8. Classify unmapped audio conservatively:
   - `MAPPED` — a production runtime mapping is recovered.
   - `EXPECTED_UNMAPPED` — known source asset, but no production mapping is currently recovered. Review only; never auto-delete.
   - `UNEXPECTED_ORPHAN` — unexpected asset with no production mapping. High-priority review; still never auto-delete.
   - diagnostic/test references do not count as production mappings.
9. Generate a prioritized review pack:
   - `P0` — blocker: broken runtime reference or error-severity source/metadata finding.
   - `P1` — high review: unexpected orphan or warning-severity audio finding.
   - `P2` — mapping review: expected source audio without recovered production mapping.
   - `P3` — informational QA item.
   - `P4` — mapped and clean under current evidence.
10. Validate the manifest and re-hash the source tree to prove it is unchanged.

## Usage

Preferred one-command AL-POC-01 run:

    python tools/audio_lab/oa_audio_run_poc.py /path/to/ATDEMO

Individual stages remain available:

    python tools/audio_lab/oa_audio_scan.py /path/to/ATDEMO
    python tools/audio_lab/oa_audio_validate.py .tmp/audio_lab/al_poc_01/audio_manifest.json --source-root /path/to/ATDEMO
    python tools/audio_lab/oa_audio_reference_audit.py .tmp/audio_lab/al_poc_01/audio_manifest.json
    python tools/audio_lab/oa_audio_review_pack.py .tmp/audio_lab/al_poc_01/audio_manifest.json .tmp/audio_lab/al_poc_01/audio_reference_report.json --source-root /path/to/ATDEMO

Outputs:

- `audio_manifest.json`
- `audio_inventory.csv`
- `audio_qa_report.json`
- `audio_qa_report.html`
- `audio_reference_report.json`
- `audio_review_pack.json`
- `audio_review_pack.html`
- `al_poc_01_summary.json`

The JSON manifest intentionally has no wall-clock timestamp, so two scans of unchanged inputs produce byte-identical manifests.

## QA codes

- `AUD001_MALFORMED_CONTAINER` — invalid/unreadable container
- `AUD002_ZERO_LENGTH` — empty source file
- `AUD003_RIFF_SIZE_MISMATCH` — RIFF size/header anomaly
- `AUD003_TERMINAL_PAD_MISSING` — odd terminal RIFF chunk lacks alignment pad; source remains untouched
- `AUD004_UNSUPPORTED_WAV_CODEC` — WAV is not supported PCM
- `AUD005_SUSPICIOUS_SILENCE` — long leading/trailing near-silence
- `AUD006_CLIPPING` — high fraction of digital-extrema samples
- `AUD007_FINGERPRINT_MISMATCH` — source hash differs from recovered/committed evidence
- `AUD009_MISSING_EXPECTED_ASSET` — expected demo-corpus asset is absent
- `AUD010_NO_RUNTIME_REFERENCE` — asset has no currently recovered runtime mapping
- `AUD011_DUPLICATE_CONTENT` — multiple paths share the same content hash
- `AUD012_METADATA_MISMATCH` — channels/sample-rate/bit-depth differ from recovered IR
- `AUD013_EXPECTED_EVIDENCE_CONFLICT` — committed fingerprint evidence disagrees internally

Reference-audit blockers use the `AUDREF...` family and are kept separate from source/container QA.

## AL-POC-01 acceptance gate

For a canonical demo-source scan:

- all 30 recovered demo audio assets are discovered;
- every discovered source has a stable SHA-256;
- recovered-corpus completeness is true;
- no error-severity QA finding exists;
- no broken runtime reference exists;
- the review pack contains no P0 blocker;
- a repeated scan produces an identical `audio_manifest.json`;
- validation with `--source-root` confirms the source-tree digest and file count are unchanged;
- Audio Lab CI is green.

Runtime-reference coverage is deliberately **not** a completeness gate. A known source asset without a recovered mapping remains a review item rather than being mislabeled as dead content.

## Deferred

AL-POC-01 does not perform denoise, resampling, loudness normalization, AI restoration, or runtime replacement. Spectrogram generation and deeper perceptual analysis are candidates for AL-POC-02 after canonical source validation and review of the AL-POC-01 pack.
