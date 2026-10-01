# KG-001 Inventory HUD v157

This increment closes the source-documented carried-object list in the classic HUD without creating a second gameplay inventory.

## Source binding

- The official demo README states that the left HUD box lists carried objects and is scrollable with the arrow keys.
- `INVBACK2.PCX` is 103x69.
- A pixel-exact comparison against `HUD3.PCX` places `INVBACK2.PCX` at logical framebuffer coordinate **(70,345)**.
- `INVFONT.PCX` is a 1380x12 source strip resolved as 138 fixed 10x12 cells. The contiguous character map starts at codepoint 35 (`#`); e.g. cell 13 is `0` and cell 30 is `A`. v157 renders inventory text directly from this source texture with nearest filtering.

## Runtime rule

`DemoState.inventory` remains the only source of truth. The menu listens to `inventory_changed`; save/load already serializes the canonical inventory dictionary, so restoring a save refreshes the same HUD list automatically.

Demo labels are source-backed:

- `rusty_tongs` -> `Rusty tongs`
- `well_key` -> `Key`
- `r8_lens` -> `Lens`
- `shield` -> `Shield`

Unknown future/retail IDs are deliberately not converted into invented player-facing labels. Cursor Up/Down may scroll the list, but the menu does not consume those events, preserving the README-documented movement bindings. They are exposed in the debug snapshot until a source-backed label mapping is available.

## Regression path

The v157 runtime runner checks:

1. empty inventory,
2. tongs acquisition/removal,
3. Well Key acquisition,
4. lens acquisition and `R8_LENS_PLACE` removal,
5. `R8_TAKE_SHIELD` acquisition,
6. save -> reset -> load inventory restoration,
7. unmapped IDs remain hidden but diagnosable.


## v173 carried-object correction

Executable dispatcher analysis verifies that opcode 0x08 appends a WORLD object index to the carried-object set and updates the carried UI; opcode 0x09 is its paired inverse. The HUD therefore follows canonical acquisition order rather than a fixed runtime item order.

Additional source-backed demo labels are now bound from WORLD:

- `parchment_r1` -> `Page - Apr 1194` (r1p1)
- `tapestry_piece_1` -> `Tapestry Piece` (r3t1)
- `tapestry_piece_3` -> `Tapestry Piece` (r8t3)
- `tapestry_piece_4` -> `Tapestry Piece` (r8t4)

These objects participate in verified remove/carry/book action groups. Their carried-state must therefore be visible in the source HUD rather than hidden as unmapped runtime IDs.
