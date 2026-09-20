# Audio Lab

Source-safe audio inventory, evidence validation, runtime-reference audit, prioritized review tooling, and milestone gating for OpenAzrael.

Preferred entrypoint:

    python tools/audio_lab/oa_audio_run_poc.py /path/to/source-audio

Individual tools:

    python tools/audio_lab/oa_audio_scan.py /path/to/source-audio
    python tools/audio_lab/oa_audio_validate.py .tmp/audio_lab/al_poc_01/audio_manifest.json --source-root /path/to/source-audio
    python tools/audio_lab/oa_audio_reference_audit.py .tmp/audio_lab/al_poc_01/audio_manifest.json
    python tools/audio_lab/oa_audio_review_pack.py .tmp/audio_lab/al_poc_01/audio_manifest.json .tmp/audio_lab/al_poc_01/audio_reference_report.json --source-root /path/to/source-audio

Contract: `data/audio_lab/al_poc_01_contract.json`

See `docs/AUDIO_LAB_AL_POC_01.md` for the source-safety rules, mapping policy, review priorities, and acceptance gates.
