# Candidate 4 Frozen Release Workflow

This workflow prevents a successful asset-backed preflight from being followed by an unnoticed source or runtime-asset mutation.

## Local release sequence

1. Checkout the exact intended source SHA and require a clean tracked worktree.
2. Run the full Candidate 4 asset-backed preflight. It must emit a PASS `.tmp/kg001/candidate4_preflight_receipt.json`.
3. Run `python tools/freeze_candidate4_release.py`.
4. The freeze receipt records exact commit SHA, Git tree SHA, preflight receipt SHA-256 and a canonical digest of every runtime asset identity already bound by preflight.
5. Do not modify source, evidence or runtime assets after freeze. Any mutation invalidates export and requires a fresh preflight/freeze cycle.
6. Export only with `python tools/export_candidate4.py`. The exporter rechecks the freeze, the individual preflight evidence and every runtime asset before creating EXE/PCK.
7. Complete packaged parity/music checks and then manual G10 on that exact EXE/PCK pair.

## GitHub source snapshot

The `Candidate 4 source snapshot` workflow is source-only. For a frozen handoff, dispatch it with the exact expected SHA. It checks out that commit, records commit/tree identity and creates the archive with `git archive`.

The artifact intentionally excludes ignored commercial/runtime assets. It is a source provenance artifact, not a replacement for the private asset-backed preflight/freeze receipt.

## Proof capture evidence

After a PASS Candidate 4 preflight and a PASS frozen-release receipt, a supplemental real-runtime proof video can be produced with:

`python tools/capture_candidate4_proof_video.py`

The capture runs the chained PPPV playthrough again in graphical Godot Movie Maker mode using the production player camera and production interactions. It then re-evaluates that captured run and requires its semantic replay fingerprint and final state hash to match the already-PASS deterministic PPPV runs. Only then is the raw movie transcoded to MP4 and a hash-bound v151 proof-capture receipt emitted.

The proof video is strong visual/runtime evidence, but it is not a substitute for packaged EXE/PCK parity or manual G10.

## Protection boundary

Repository branch protection/rulesets are useful administrative controls but are not treated as release evidence. The cryptographic source/runtime freeze remains required even if branch protection is later enabled.

Candidate 4 is not Known Good merely because a source snapshot or freeze receipt exists.
