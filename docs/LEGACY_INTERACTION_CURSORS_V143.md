# Legacy interaction cursors v143

OpenAzrael v143 restores the complete **35-file** cursor corpus from the official demo's `ATDEMO/MICE` directory.

## Fidelity rules

- Cursor artwork is never redrawn or AI-generated.
- Source PCX files are fingerprint-checked against `data/ui/legacy_cursor_manifest_v143.json`.
- Runtime PNGs preserve source RGB exactly and use only palette index 0 as transparency.
- No resize/resampling occurs during conversion; Godot displays the source pixels at integer 2x scale with nearest filtering.
- The original B-prefixed variants are restored but remain **HOLD_UNRESOLVED** until their exact executable-level semantics are proven.

## Current demo bindings

- `TAKE`: loose pickups, drained lens, exposed Shield.
- `USE`: doors where push/pull direction is not source-proven, using tongs on the Well Key, placing/using puzzle items.
- `PULL`: R7 right-most lever (`well_lev02`).
- `ROT`: R7 lower-right wheel (`well_weel3`) and R8 tapestry rotation.
- `CANT`: interactive target whose current prerequisite is not satisfied.
- `POINTER`: no interactive target under the production interaction ray.

The artwork is source-exact. Per-object cursor associations above are explicit OpenAzrael semantic bindings where the exact 1996 executable binding has not yet been recovered.

## Candidate gate

`kg001_interaction_cursor_runner_v143.gd` checks the complete restored cursor asset corpus, HUD integration and dynamic cursor states. Candidate export remains blocked unless this runtime test passes with restored assets.
