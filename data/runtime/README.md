# Generated runtime framework metadata

This directory is the staging location for small, source-safe metadata included
in candidate Godot builds.

Generated JSON files in this directory are intentionally ignored by Git. They
may be staged from individual artifacts or directly from a
`kg001_framework_bundle.json` with:

    python -m tools.remaster_framework.runtime_metadata stage ...

Supported staged artifacts:

- `build_provenance.json` — required by the KG framework bundle;
- `release_gate_summary.json` — required by the KG framework bundle;
- `pppv_coverage.json` — required by the KG framework bundle;
- `pppv_playthrough_evaluation.json` — optional; present only after a chained
  real-player playthrough has actually been evaluated.

The stager validates JSON schema, keeps every referenced bundle artifact inside
the bundle directory, and verifies internal self-hashes for build provenance and
release summary before copying them into the runtime tree.

F11 bug-report capture includes staged files only when they are present, below
the size limit, valid JSON, and match the expected schema. Missing optional
metadata never disables F11.

These files must contain metadata/evidence only. Original commercial game assets
must never be staged here.
