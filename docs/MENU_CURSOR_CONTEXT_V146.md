# Menu ↔ Cursor Context v146

v146 closes the integration gap between the source-derived v143 interaction cursors and the v145 classic menu/HUD.

## Runtime rules

- The interaction cursor now lives in a dedicated CanvasLayer at layer 100.
- LegacyMenuV145 remains at layer 50, so the pointer/action icon is never hidden behind TITLE, HUD or SAVE13 artwork.
- In graphical mode the source cursor follows the real viewport mouse position.
- While the title screen or service menu is modal, the cursor is forced to the original POINTER artwork. World-space TAKE/USE/PULL/ROT/CANT states behind the panel are not exposed.
- Outside modal menu states the v143 InteractionProbe context remains authoritative.

## Service action regions

The six SAVE13 actions use pairwise non-overlapping, source-label-constrained regions. These regions are deliberately described as evidence-constrained rather than exact original hitboxes. Exact 1996 input extents remain HOLD until original runtime/executable evidence resolves them.

This gate does not invent menu art or cursor art.
