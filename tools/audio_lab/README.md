# Audio Lab

Source-safe audio inventory, evidence validation, runtime-reference audit, prioritized review tooling, and milestone gating for OpenAzrael.

Preferred entrypoint:

    python tools/audio_lab/oa_audio_run_poc.py /path/to/source-audio

Individual tools:

    python tools/audio_lab/oa_audio_canonical_verify.py /path/to/source-audio --output .tmp/audio_lab/al_poc_01/canonical_source_report.json
    python tools/audio_lab/oa_audio_scan.py /path/to/source-audio
    python tools/audio_lab/oa_audio_validate.py .tmp/audio_lab/al_poc_01/audio_manifest.json --source-root /path/to/source-audio
    python tools/audio_lab/oa_audio_reference_audit.py .tmp/audio_lab/al_poc_01/audio_manifest.json
    python tools/audio_lab/oa_audio_review_pack.py .tmp/audio_lab/al_poc_01/audio_manifest.json .tmp/audio_lab/al_poc_01/audio_reference_report.json --source-root /path/to/source-audio
    python tools/audio_lab/oa_audio_repo_evidence.py --output .tmp/audio_lab/repo_evidence.json
    python tools/audio_lab/oa_audio_repo_drift.py --output .tmp/audio_lab/repo_mapping_drift.json

Contract: `data/audio_lab/al_poc_01_contract.json`

See `docs/AUDIO_LAB_AL_POC_01.md` for the source-safety rules, mapping policy, review priorities, and acceptance gates.

Canonical corpus evidence: `data/audio_lab/al_poc_01_canonical_source_evidence.json`.
Repository mapping baseline: `data/audio_lab/al_poc_01_repo_mapping_baseline.json`.
