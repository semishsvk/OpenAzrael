# KG-001 Candidate 1 diagnostics — v116

v116 adds a diagnostic-only layer for the first real Godot integration build. It does not intentionally change puzzle or transition semantics.

## Controls

- **F6** — show/hide authored trigger volumes and trigger names.
- **F7** — show/hide Candidate diagnostics HUD.
- **F8** — existing Classic/Enhanced audio debug.
- **F9** — existing audio parity capture.
- **F10** — write a canonical runtime state dump.
- **F11** — capture a source-safe bug-report ZIP (screenshot + state + telemetry tail + system info + optional build validation context).
- **1 / 2 / 3** — existing debug room jumps; now logged.

## Candidate HUD

The F7 HUD displays the exact build/checkpoint watermark, current room, player XYZ, canonical DemoState SHA-256, active flags, active puzzle nodes, value keys, last trigger edge, last diagnostic event, last logical audio event and the JSONL event-log path.

## Event log

Non-headless builds append structured events to:

`user://openazrael_candidate1_events.jsonl`

The log includes state hashes and covers inventory changes, flags, puzzle nodes, logical audio, interactions, trigger enter/exit edges, room transitions, room loads, debug room jumps and state dumps.

Headless KG-001 runners keep the same instrumentation in memory but do not append the persistent JSONL log.

## F10 state dump

F10 writes a source-safe runtime report under:

`user://openazrael_kg001_state_dump_<timestamp>_<sequence>.json`

It includes room, player XYZ, canonical persistent payload/hash, last event, last trigger, last logical audio event and the associated event-log path.

## Fail-fast asset validation

The RoomManager no longer preloads R1/R7/R8 GLBs at script-parse time. It uses runtime resource paths so Candidate Diagnostics can report a precise missing-resource list before attempting to load the first room.

Always required:
- R1/R7/R8 room GLBs;
- `data/xaf_trigger_evidence.json`;
- `data/gameplay_event_graph_v87.json`.

For a normal non-headless Candidate 1 run, the four golden Event-IR sounds used by the accepted demo route are also required:
- `S152V2.WAV`
- `S137.WAV`
- `S121.WAV`
- `799SECDR.WAV`

The v109-v111 headless tests retain capture-only logical-audio behavior and therefore do not make physical WAV presence a prerequisite.

## Trigger visualization

F6 renders translucent boxes from the authored XAF trigger bounds already used by RoomManager. This is diagnostic visualization only; it does not replace or alter transition logic.

## Evidence boundary

`tools/validate_candidate_diagnostics_v116.py` verifies the source wiring. Actual Godot execution remains **NOT_EXECUTED** until the candidate workflow is run in a Godot-capable checkout with locally restored ignored assets.

## F11 bug-report capture

F11 creates `user://openazrael_bugreport_<unix>_<sequence>.zip` without changing gameplay state. The package contains a screenshot when available, canonical DemoState snapshot/hash, the last 500 JSONL telemetry events, system metadata, a human-readable worksheet, `framework_context.json`, and a manifest declaring that excluded commercial assets are not included.\n\nCandidate-build tooling may stage `build_provenance.json`, `release_gate_summary.json`, and `pppv_coverage.json` under `data/runtime/`. F11 reads only these metadata files, enforces a 2 MiB per-file cap and expected schemas, and records SHA-256 for every included framework artifact. Missing or invalid optional metadata is reported in `framework_context.json` and does not disable bug capture.

Stable diagnostic identifiers are source-preserving: `ROOM:<room>`, `TRG:<room>:<trigger>`, `PUZ:<node>`, `FLAG:<flag>`, and `ITEM:<item>`.

The canonical reporting workflow and severity definitions are in `docs/BUG_REPORTING.md`. GitHub issue intake is provided by `.github/ISSUE_TEMPLATE/bug_report.yml`.
