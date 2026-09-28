# Classic Presentation v147

v147 makes the faithful 1996 presentation explicit rather than treating the old 640×480 HUD as a decorative overlay on a widescreen renderer.

- The logical classic frame is 640×480 (4:3).
- Any viewport area outside the scaled 4:3 frame is covered by black matte bars.
- The persistent modern Candidate HUD panel is hidden in classic mode. Debug surfaces remain available on demand through the existing F-keys.
- The source interaction cursor remains on its dedicated layer above the classic UI.
- `kg001_legacy_menu_graphical_capture_v147.gd` captures TITLE, HUD and SERVICE directly from the real Godot viewport for visual QA.

The graphical capture is deterministic engine output and never generative imagery.
