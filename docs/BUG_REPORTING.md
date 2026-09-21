# OpenAzrael bug reporting

**Checkpoint:** `v116-context-v28`  
**Candidate:** KG-001 Candidate 1

OpenAzrael uses GitHub Issues as the canonical human bug tracker. The runtime capture path is diagnostic-only and must not change gameplay state.

## In-game capture

Press **F11** during a normal graphical Candidate 1 run. OpenAzrael creates `user://openazrael_bugreport_<unix>_<sequence>.zip`.

The package contains, when available:

- `report.json`
- `report.txt`
- `state.json`
- `system_info.json`
- the last 500 events as `events_tail.jsonl`
- `screenshot.png`
- `framework_context.json`
- `manifest.json`

A candidate build may additionally contain generated, source-safe framework
metadata. F11 includes each artifact only when it exists, is below the 2 MiB
limit, parses as JSON and matches its expected schema:

- `build_provenance.json` — exact candidate commit/version/input identities;
- `release_gate_summary.json` — build-level Known-Good gate status;
- `pppv_coverage.json` — build-level physical-player gameplay coverage.

Every included framework artifact is SHA-256-bound in the F11 manifest.

These artifacts describe the build. The event tail, screenshot and runtime state
describe the concrete play session in which the bug was captured. Missing
framework metadata never disables F11.

The package deliberately excludes room GLBs, original audio, textures and other
commercial payloads.

## Stable diagnostic IDs

Use source-preserving deterministic IDs instead of invented sequential numbers:
`ROOM:<room>`, `TRG:<room>:<trigger>`, `PUZ:<node>`, `FLAG:<flag>`, and
`ITEM:<item>`.

## GitHub issue workflow

Create a new issue with the **OpenAzrael bug report** form and attach the F11 ZIP.
Record the summary, reproduction steps, expected/actual behavior, reproducibility
and severity. If framework metadata is present, the ZIP already contains the
candidate provenance and validation context; do not manually guess a commit SHA.

- **Critical** — crash, corrupted/lost persistent state, or progression-blocking softlock.
- **Major** — important gameplay/system behavior is wrong but progress remains possible.
- **Minor** — localized defect with a practical workaround and limited impact.
- **Cosmetic** — visual/audio/UI presentation defect with no gameplay effect.

## Fix -> regression rule

Every reproducible fixed bug should receive a regression check at the lowest
useful layer. Prefer deterministic source/unit/state-space tests; use a headless
Godot regression when physical runtime behavior is required; reserve G10 manual
coverage for behavior that cannot be automated reliably. Link the regression
evidence to the GitHub issue number.

A Critical bug or reproducible softlock blocks `demo-known-good-001` until fixed
and revalidated.
