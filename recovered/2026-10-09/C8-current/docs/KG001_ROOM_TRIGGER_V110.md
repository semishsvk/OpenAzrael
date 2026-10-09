# OpenAzrael v110 — KG-001 room/trigger runner

v110 prepares the asset-backed G04/G05 runner. Unlike v109, this test intentionally loads `main.tscn` and therefore requires locally restored `R1.glb`, `R7.glb` and `R8.glb`.

The runner first preflights the three room resources. Missing assets produce `BLOCKED_MISSING_ASSETS` with exit code 2 rather than a misleading FAIL.

## Coverage

For all four tracked demo transition triggers it calls the real `RoomManager._inside_trigger()` implementation and checks a centroid point as inside plus a point beyond the X/Z maxima as outside.

It then drives the real room manager through:
- locked R1 -> R7 must remain R1;
- opened R1 -> R7 must enter R7;
- R7 -> R1;
- locked R1 -> R8 must remain R1;
- opened R1 -> R8 must enter R8;
- R8 -> R1;
- persistent inventory survives room replacement/re-entry.

The transition definitions remain sourced from `data/xaf_trigger_evidence.json`; the runner does not invent a second portal map.

## Intended execution

After restoring the excluded room assets, import resources and run:

```bash
godot --headless --path . --import
godot --headless --path . --script res://scripts/kg001_room_trigger_runner_v110.gd
```

Current status is **SOURCE_CONTRACT_PASS / GODOT_RUNTIME_NOT_EXECUTED** in this environment.
