# Classic Menu / HUD Runtime v145

v145 turns the v144 forensic inventory into a functional source-constrained classic UI.

## Proven mappings

The original demo README plus pixel-exact matching against `HUD3.PCX` bind the three HUD controls:

- `NBUT0` at source rect `235,343,83,36` -> **SCAN**
- `NBUT1` at source rect `213,381,77,42` -> **MAP**
- `NBUT2` at source rect `363,386,90,43` -> **LOAD/SAVE + volume service panel**

`SAVE13.PCX` is the final source service-panel frame and visibly contains **load / save / music / sfx / quit / confirm**. The original executable contains five source file names, `FILE ALPHA` through `FILE EPSILON`, and the filename pattern `SAVE%d.dat`.

## Runtime behavior

- Classic UI operates on a logical 640x480 canvas and scales as one unit.
- Original HUD/menu artwork is restored from ATDEMO and remains Git-ignored.
- The interaction ray follows the visible mouse cursor in graphical mode.
- Held RMB performs head-look, matching the demo README; headless PPPV retains deterministic synthetic mouse input.
- LOAD/SAVE/QUIT are pending actions and execute only through CONFIRM.
- Five save slots preserve DemoState, current room, player XYZ, yaw and pitch.
- MUSIC and SFX bind to the corresponding Godot bus where present and fall back to Master.
- M toggles map state. The original map-rendering subsystem itself remains HOLD; no synthetic classic map geometry is invented.
- SCAN uses the current mouse-ray target and source-proven scan status strings.

## Still HOLD

The following are not guessed:

- exact original screen origin of the 206x170 service panel,
- exact title-screen dismissal gesture,
- exact 1996 bitmap-font glyph lookup table,
- original map rendering,
- exact music/SFX adjustment gesture and scale,
- exact timing of SAVE00-SAVE13 and REPLAY0-REPLAY7 animation sequences.

The current service-panel origin is evidence-constrained and explicitly marked pending original runtime capture. None of the HOLD items may be presented as recovered 1996 fact.

## Acceptance

v145 source validation and the 42-file source-art restore must pass. Candidate promotion additionally requires the Godot asset-backed v145 runner.
