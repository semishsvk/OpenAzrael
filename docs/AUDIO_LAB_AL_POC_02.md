# OpenAzrael Audio Lab — AL-POC-02

## Goal

AL-POC-02 adds deterministic spectral QA on top of the source-safe AL-POC-01 corpus validation. It remains strictly read-only: no source WAV is rewritten, normalized, denoised, resampled, padded, restored, or replaced.

Prerequisite evidence: `data/audio_lab/al_poc_01_canonical_source_evidence.json` must remain PASS.

## Canonical corpus

The canonical 30-WAV demo corpus has the source-tree SHA-256:

`d7a283d07b948249827d026d932dd5716101f48e452112f1248c95dd5cb47cba`

AL-POC-02 was run against all 30 canonical assets with zero decode errors and finite numerical metrics for every asset.

Committed real-corpus evidence:

- `data/audio_lab/al_poc_02_canonical_spectral_evidence.json`
- spectral analysis fingerprint: `e7a59c119359a9544c89d2c2bc56afd8649f0fbf86e9dbfb7c1a1fdb2decb3c4`

The fingerprint covers deterministic spectral metrics only. It intentionally excludes review annotations, HTML paths, spectrogram filenames, and other presentation data.

## Analysis

Default parameters:

- FFT size: 512
- hop size: 128
- spectrogram display floor: -64 dB
- spectrogram preview: 256 × 128
- robust outlier threshold: |z| >= 3.5

Per asset:

- dominant frequency
- spectral centroid
- spectral bandwidth
- 85% spectral rolloff
- spectral flatness
- high-frequency energy ratio
- DC offset
- RMS and peak
- crest factor
- zero-crossing rate
- peak position
- temporal energy centroid
- 10/50/90% cumulative-energy positions
- 10–90% energy span
- first/last 10% energy ratios
- deterministic grayscale spectrogram PNG

The -64 dB display floor was calibrated visually on the canonical 8-bit corpus. It reduces visible quantization background while retaining weaker spectral structure. This parameter affects review images, not the numerical spectral fingerprint.

## Temporal QA

Temporal metrics were added after the first spectral-only baseline. This intentionally changed the analysis fingerprint from `b4037a954e7fb0c1dd4a08337ae8096fa48b12dea3f6a97d4400e0a18201a093` to the current `e7a59c119359a9544c89d2c2bc56afd8649f0fbf86e9dbfb7c1a1fdb2decb3c4`, while the canonical source-tree hash remained unchanged.

Temporal distribution extremes are **not** part of the current outlier score. They are review context only. This avoids treating legitimate game-SFX timing, delayed impacts, long tails, or front-loaded transients as defects.

## Review-only outliers

The robust median/MAD layer is deliberately non-authoritative. A flagged asset remains a PASS.

Canonical review shortlist currently contains 8 assets, each for one metric:

- `EUGROAR.WAV` — high absolute DC offset
- `SCAN.WAV` — high absolute DC offset
- `HUD3.WAV` — high crest factor
- `S134.WAV` — high crest factor
- `S174ELP1.WAV` — high crest factor
- `S182.WAV` — high zero-crossing rate
- `SPAPER.WAV` — high zero-crossing rate
- `SR27KEYS.WAV` — high zero-crossing rate

These findings mean only “unusual relative to the 30-file corpus”. They do **not** imply corruption, poor quality, a restoration target, or a runtime bug.

Metrics with strongly skewed positive distributions use a log10 transform before robust-z calculation. Very low absolute DC offset is explicitly not treated as a review concern.

## Usage

Install the spectral dependency:

    python -m pip install -r tools/audio_lab/requirements-spectral.txt

Run the canonical analysis:

    python tools/audio_lab/oa_audio_spectral.py /path/to/original_audio --output-dir .tmp/audio_lab/al_poc_02

Compare a real-corpus run with the committed baseline:

    python tools/audio_lab/oa_audio_spectral_baseline.py .tmp/audio_lab/al_poc_02/spectral_manifest.json

Outputs:

- `spectral_manifest.json`
- `spectral_review.html`
- `spectrograms/*.png`

## Source-safety gates

AL-POC-02 fails when:

- the source audio tree changes during analysis;
- a WAV cannot be decoded by the supported PCM path;
- a required numerical metric is non-finite;
- the requested output path is equal to or inside the source tree.

A distribution outlier never causes a failure.

## Baseline drift

The comparator distinguishes three important cases:

- `source_tree_sha256` drift — the canonical input bytes changed;
- `asset_count` drift — corpus completeness changed;
- `analysis_fingerprint_sha256` drift — the spectral algorithm or its numerical results changed.

A fingerprint change is not automatically bad, but it must be intentional and reviewed before updating the committed evidence.

## Deferred

Still explicitly out of scope for AL-POC-02:

- denoise
- resampling
- loudness normalization
- AI restoration/reconstruction
- enhanced asset generation
- runtime asset replacement
- automatic subjective quality scoring

Those belong only in a later milestone after POC-02 review is complete.
