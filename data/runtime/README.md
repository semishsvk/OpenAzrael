# Generated runtime framework metadata

This directory is the staging location for small, source-safe metadata included
in candidate Godot builds.

Generated JSON files in this directory are intentionally ignored by Git. They
may be created during a clean candidate build with:

    python -m tools.remaster_framework.runtime_metadata stage ...

Supported staged artifacts:

- `build_provenance.json`
- `release_gate_summary.json`
- `pppv_coverage.json`

F11 bug-report capture includes these files only when they are present, below the
size limit, valid JSON, and match the expected schema. Missing metadata never
disables F11.

These files must contain metadata/evidence only. Original commercial game assets
must never be staged here.
