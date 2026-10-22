# Legacy scanner / suit boot v164

Status: source-backed implementation for KG-001 demo rooms.

## Restored behavior

- Suit boot uses original `HUDMES.DAT` rows 3..15 and the original `HUD3.WAV`.
- Entering/loading demo rooms drives the upper-right environment readout from original `HUDMES.DAT` room messages and `SCAN.WAV`.
- Demo bindings: R1 -> message 87, R7 -> 101, R8 -> 97.
- The readout uses the source `RUSGLD2.PCX` gold HUD font strip restored to a transparent runtime PNG.
- `RoomManager.room_changed` is observational only: scanner presentation never changes player position, velocity, puzzle state, or room traversal.

## Fidelity boundary

Exact per-line/per-character timing, original glyph advance metrics, and the final pixel-exact text origin/wrap width are not yet proven from the executable. Runtime therefore uses only source-audio event boundaries and a screenshot-calibrated upper-right rectangle, and records this limitation explicitly.

`REPLAY0-7.PCX`, zero-filled `RANIM0-4.ANM`, EUGENE/EUGENB object scans, and `HUDTOP.RES`/`HUDBOT.RES` are not substituted for the environment scanner without direct evidence tying them to this sequence. No AI/synthetic scanner imagery is used.
