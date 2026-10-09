# Menu Lab v144 — source-faithful menu/HUD reconstruction

Menu Lab starts with the original ATDEMO evidence and deliberately avoids inventing a conventional modern main menu.

## Proven source scope

The demo contains the original 1996 title image (`TITLE.PCX`), complete HUD frames (`HUD3.PCX`, `HUDOFF.PCX`), three ON/OFF HUD button pairs, eight `REPLAY*.PCX` frames, fourteen `SAVE*.PCX` previews, inventory/map UI art and three 12-pixel-high font strips.

The original README explicitly documents the HUD controls:
- top-left: scan,
- button below it: map,
- right-hand button: load/save box and volume,
- M: map/external-view toggle,
- left HUD box: carried-object list with arrow-key scrolling.

The original R.EXE independently references the title, HUD, save-preview/save-data, replay/restart and HUD data resources.

## Fidelity rules

1. Classic mode uses source art only.
2. No guessed New Game / Options / Quit layout is introduced for the demo.
3. Unknown button mapping, coordinates, font glyph tables, alpha rules and animation timings remain HOLD.
4. A later modern menu may exist as a separate presentation layer, never as evidence for the 1996 reconstruction.
5. Menu screenshots used for validation must be real deterministic runtime output, never generative imagery.

## Development order

1. Source inventory + hashes (v144).
2. Decode/restore UI art without resampling.
3. Recover font glyph map and button semantics from executable/data/capture evidence.
4. Reproduce title flow.
5. Reproduce HUD scan/map/load-save-volume controls.
6. Reproduce save/load panel and REPLAY/RESTART state.
7. Add graphical pixel/census tests against captured original output.
8. Only after classic parity: optional modern/responsive menu skin.
