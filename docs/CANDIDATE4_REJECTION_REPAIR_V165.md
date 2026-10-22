# Candidate 4 rejection repair (2026-09-27)

Candidate 4 remains REJECTED. No new Candidate identity is allocated by this repair.

## Provenance and diagnosis

Authoritative baseline: integration/kg001-candidate3-pppv-v2 at
e9de18a794bba187201c9865dbf897454610857c (tree 7458762053be86a2ebf45a539e1789d0b62938f7).
The locally delivered Candidate 4 is from 274781e9864c92c91e838f77abbb9e50ce0acfb8.
Its PCK SHA-256 is 9cd4a2986e2ff3e1575a0f593c2efed2e862538be81ed6a71feeabbd187ce677.
Godot inspection of that historical PCK found no v145 menu script, HUD3, INVFONT,
POINTER image, or Niamh/Conv resource. Do not use it as a new export base.

| Issue | Source implementation | Generated asset | Scene/runtime wiring | Historical packaged runtime | Verdict |
|---|---|---|---|---|---|
| Menu | Existing v145/v149 | Existing restoration rebuilds PCX menu art | main.tscn instantiates LegacyMenuV145 | Menu script and HUD3 absent | STALE BUILD/EXPORT |
| Cursor | Existing v143/v146 | 35 original cursor PNGs restored | HUD's inherited processing stopped during menu pause; repaired with PROCESS_MODE_ALWAYS | POINTER absent | SOURCE BUG CONFIRMED |
| Inventory/items | Existing v157, DemoState signals and INVFONT glyphs | INVFONT restored from original PCX | Existing acquisition/removal/save-load UI binding reused | INVFONT and menu absent | STALE BUILD/EXPORT |
| Required character animation | R7/zxactghost dispatches Niamh/Conv | NIAMH.ANI identified but no decoded Conv.tres or imported clip | Dispatcher explicitly reports HOLD_SOURCE_CLIP_MISSING | Clip absent | SOURCE BUG CONFIRMED |
| KEYHOLE | Existing v133 global Trimesh UV adapter | Clean restoration preserves source UVs and embedded pixels | Strengthened v124 checks actual world transform/material UV direction | Old build predates current repair state; visual orientation not re-certified | FIX EXISTS AND IS WIRED |
| Third demo room windows | Existing v133; third demo room is internally R8, not R3 | All 10 vertical BAP* sentinels rebuilt | Strengthened v124 checks named source texture bindings and world-space UV direction | Old build not re-certified | FIX EXISTS AND IS WIRED |

Animation verdict describes incomplete source support, not a new fabricated decoder
or a claim that the original game lacked animation. The source contract v138
explicitly holds exact keyframes/timing pending decode. A valid required-clip test
must remain BLOCKED until an evidence-backed converter and playback are available.
The v118 well/tongs event is a source-backed same-group visibility/audio sequence;
its contract explicitly does not require an invented continuous tween.

## Minimal repairs

- Keep the existing HUD cursor processing during title/service pause. The v146
  regression now waits for natural frame processing instead of directly calling
  the cursor updater (which concealed the regression).
- Include scanner FileAccess JSON and built-in localization JSON in current
  export presets. The export contract test is part of Candidate 4 preflight.
- Reject malformed save JSON with JSON.parse and the existing rejection event;
  do not emit a Godot ERROR for an expected invalid-user-save test case.
- Extend v124 runtime validation with one KEYHOLE and ten original vertical
  window sentinels. Validate the production mesh transform, active material,
  source texture binding and UV orientation, not just asset presence.
- Align two stale tests with existing production source: Niamh is authored
  visible before activation; mirror01/broken3 are pane/shard overlays excluded
  from floor semantics so the mirror opening remains traversable. No floor,
  collision, transition or puzzle production implementation was changed.

## Acceptance boundary

The required v137 animation gate remains BLOCKED_SOURCE_ANIMATION, even when all
other trigger checks pass. Source tests, headless full-demo and individual physical
routes do not replace a fresh packaged production START-to-demo_complete run.
Do not export/promote a new Candidate based on this repair while that gate fails.
No historical Candidate evidence is rewritten.
