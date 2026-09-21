# OpenAzrael bug reporting

**Checkpoint:** `Candidate 3 preflight / diagnostics v116`  
**Candidate:** KG-001 Candidate 3

OpenAzrael uses GitHub Issues as the canonical human bug tracker. The runtime capture path is diagnostic-only and must not change gameplay state.

## In-game capture

Press **F11** during a normal graphical Candidate 3 run. OpenAzrael creates `user://openazrael_bugreport_<unix>_<sequence>.zip`.

The package contains, when available: `report.json`, `report.txt`, `state.json`, `system_info.json`, the last 500 events as `events_tail.jsonl`, `screenshot.png`, and `manifest.json`.

The package deliberately excludes room GLBs, original audio, textures and other commercial payloads.

## Stable diagnostic IDs

Use source-preserving deterministic IDs instead of invented sequential numbers: `ROOM:<room>`, `TRG:<room>:<trigger>`, `PUZ:<node>`, `FLAG:<flag>`, and `ITEM:<item>`.

## GitHub issue workflow

Create a new issue with the **OpenAzrael bug report** form and attach the F11 ZIP. Record the summary, reproduction steps, expected/actual behavior, reproducibility and severity.

- **Critical** — crash, corrupted/lost persistent state, or progression-blocking softlock.
- **Major** — important gameplay/system behavior is wrong but progress remains possible.
- **Minor** — localized defect with a practical workaround and limited impact.
- **Cosmetic** — visual/audio/UI presentation defect with no gameplay effect.

## Fix -> regression rule

Every reproducible fixed bug should receive a regression check at the lowest useful layer. Prefer deterministic source/unit/state-space tests; use a headless Godot regression when physical runtime behavior is required; reserve G10 manual coverage for behavior that cannot be automated reliably. Link the regression evidence to the GitHub issue number.

A Critical bug or reproducible softlock blocks `demo-known-good-001` until fixed and revalidated.

## F11 v2 physical context

The F11 ZIP now captures collision diagnostics in addition to the screenshot,
state and event tail. `report.json` / `state.json` include:

- player velocity, `is_on_floor`, floor normal, snap length, max slope and safe margin;
- a downward support ray (`support_below`);
- a vertical X/Z column probe (`column_probe`) that can reveal an authored floor
  above a player who has already fallen through it;
- current slide collisions;
- nearby layer-1 collision bodies found with a non-mutating sphere query;
- the exact exported source commit and Godot version when
  `data/runtime_build_identity.json` was embedded by the guarded exporter.

These fields are observational only. F11 does not create collision, teleport the
player, mutate puzzle state or include commercial room/audio/texture assets.
