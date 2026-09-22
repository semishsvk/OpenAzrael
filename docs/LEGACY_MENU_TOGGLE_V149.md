# Legacy service-menu toggle v149

The official demo documents the right-hand HUD control as the control that brings up the load/save box and adjusts volume. The original service graphics also preserve the state machine:

- SAVE00–SAVE06: closed → fully open construction sequence.
- SAVE06: stable open panel.
- SAVE07: SAVE highlighted.
- SAVE08: LOAD highlighted.
- SAVE09: MUSIC highlighted.
- SAVE10: SFX highlighted.
- SAVE11: QUIT highlighted.
- SAVE12: SAVE confirmation state.
- SAVE13: LOAD confirmation state.

There is no separate close control in the service-panel art. The OPTIONS/NBUT2 HUD hotspot remains available at the lower-right edge of the expanded panel. v149 therefore treats the same source OPTIONS control as a toggle: left-click once to open, left-click again to close.

RMB is **not** used to close the menu. In the original control scheme RMB is the held head-look control, while ESC is documented for skipping conversation responses.

The frame order is source-proven. Exact 1996 animation timing remains HOLD until runtime capture/executable evidence resolves it; v149 does not invent that timing.
