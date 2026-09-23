# OpenAzrael Git Baseline

The GitHub repository is the **source-safe versioned mirror**, not a redistribution archive of *Azrael's Tear* assets.

## Authoritative development line

- Active integration: `integration/kg001-candidate3-pppv-v2`.
- Candidate source identity is the exact Git commit/tree, not historical internal labels such as v106/v116.
- Historical context tags remain provenance only; they are not the current release baseline.

## Git contains

- Godot source, scenes and configuration;
- Python import/forensic/build/validation tooling;
- canonical machine-readable contracts and source-safe evidence metadata;
- documentation and versioning policy;
- hashes/fingerprints of excluded private inputs where needed for validation.

## Git excludes

- original commercial game payloads;
- directly derived room/audio/texture/UI payloads from the commercial/demo data;
- executable/dump material;
- build/export outputs, checkpoint archives and caches;
- reproducible forensic payloads containing commercial-derived bytes.

## Candidate 4 freeze policy

A release candidate handoff is frozen **after** exact-SHA asset-backed preflight with `tools/freeze_candidate4_release.py`. The local receipt contains only identities/hashes and binds the exact source tree, preflight receipt and complete runtime asset set.

The source-only GitHub snapshot workflow may archive an explicitly requested exact commit with `git archive`. It does not upload private runtime assets.

No Candidate 4 or KG-001 Known Good tag is permitted before exact-SHA asset-backed runtime, guarded packaged/export and manual G10 evidence are all complete.
