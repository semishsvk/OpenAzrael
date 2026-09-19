# OpenAzrael v109 — source-safe Godot headless KG-001 runner

v109 prepares the first Godot-executable KG-001 slice that does not require the excluded room, texture or WAV payloads.

## Runtime changes

`DemoState` now supports `reset_all()` and `restore_canonical_state_payload()`. Restore validates the schema and pair-array structure before replacing persistent state. This enables a deterministic save/reset/restore/hash round-trip.

`LegacyEvents` now has a capture-only mode. Logical sound actions are always recorded through `captured_audio_events` / `logical_audio_event`; when capture-only is enabled, the runner does not try to load the commercial WAV file.

## Headless runner

`scripts/kg001_headless_runner_v109.gd` uses the real project autoloads and v87 Event IR without loading `main.tscn`. It defines **13 runtime assertions** and verifies:

- clean-state canonical hash;
- well-key and R7 switchboard logic;
- R8 lens / optical / secret-door / shield Event IR;
- logical audio stream `S152V2 -> S137 -> S121 -> 799SECDR`;
- completed-state canonical hash;
- reset to clean hash;
- save payload restore;
- restored hash and `demo_complete`.

Intended command:

```bash
godot --headless --path . --script res://scripts/kg001_headless_runner_v109.gd
```

## Current status

The recorded Godot 4.7.2 baseline `6528d438ab2b14d344fb0e19f83ba5d5e699cd60` is **PASS, 13 checks**; see `data/tests/kg001_headless_runtime_v109.json`. The script exits non-zero on any failed assertion and prints one `OPENAZRAEL_KG001_V109` JSON result line. Graphics/icon integration is included in the tested source.

This still does not test 3D room geometry, physical trigger volumes, actual WAV playback, original timing or Classic audio parity. Those remain later KG-001/runtime and forensic gates.
