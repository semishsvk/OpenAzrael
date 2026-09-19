# KG-001 Candidate 1 — Windows build

The final tested source is `6528d438ab2b14d344fb0e19f83ba5d5e699cd60`, including main
`43637474b4bddc34fcf38355901352f505c0c2a4`. Canonical documentation is
`v116-context-v26`; the requested application watermark stays
**KG-001 Candidate 1 / v116-context-v24**.

## Verified results

`python tools/run_kg001_candidate_v112.py --fresh-checkout --promote-results`
completed successfully with Godot `4.7.2.stable.official.ed1daf0bf`.
The checkout was clean before and after import/tests. All restored room files
were present and ignored; no forbidden payload was tracked.

| Gate | Result |
|---|---|
| G00 context/evidence integrity | PASS |
| G01 data validation | PASS |
| G02 gameplay logic | PASS — v109, 13 checks |
| G03 exhaustive source state-space | PASS — 63 states, 123 changed edges, 0 softlocks |
| G04 room transitions | PASS — v110 |
| G05 physical trigger semantics | PASS — v110 |
| G06 logical audio events | PASS — v109/v111 |
| G07 save/load hash | PASS — v109 |
| G08 synthetic full demo | PASS — v111, 33 checks |
| G09 fresh checkout/import | PASS |
| G10 human sanity | PENDING_MANUAL_USER |

v109/v111 match the v108 hash
`69cdb8287e548f7a31884e26c23b739ead10ed8f998318cd5690c0a3b03e7db8`
and `S152V2.WAV -> S137.WAV -> S121.WAV -> 799SECDR.WAV`.
The v110 process has a nonfatal ObjectDB cleanup warning at exit, retained in
its evidence. No ERROR or SCRIPT ERROR occurs in the final suite.

## Export and graphical checks

The source-safe `Windows Candidate 1` preset exports a Windows x86_64 debug EXE
and external PCK. Create the `exports/` directory first, then run Godot with
`--headless --path . --export-debug "Windows Candidate 1"`.
Matching official Godot templates are installed locally; their ZIP CRC and
SHA-256 provenance are included in the artifact evidence.

- EXE SHA-256: `0118115a8c1e59a2792670cc08a5fa8433bf3526133157f9a105fb1c7a8e482c`.
- PCK SHA-256: `43a1374a000a3144bec8b7f10af7f6203330d28916c430a599c2afb8ee11aaae`.
- Exported EXE headless and graphical launch smoke: PASS, exit 0, no engine errors.
- R1/R7/R8 rendered from the exported PCK through the same Godot 4.7.2 engine;
  a separate capture script uses the existing debug room navigation and disables
  player physics during screenshots. This is automated rendering evidence only.
- Supplied Sigil PNG/ICO is used by the project/export. Six standard Windows
  icon sizes (16/32/48/64/128/256) match the ICO payload exactly in the EXE.

## Restoration and integration scope

The supplied `atdemo.zip` was unpacked as nested ZIP/SFX containers without
executing its installer. `tools/restore_candidate_assets.py` rebuilds the local
assets from the extracted ATDEMO folder (numpy, Pillow, trimesh 5.1.0).
R1 has 69 primitives/593 triangles/62 textured primitives; R7 has 48/689/40;
R8 has 87/1050/74. All 86 demo AZF textures decode. Runtime WAVs are verified
against recorded original fingerprints before copying. S137 receives only a
missing terminal RIFF padding byte and corrected container length; PCM bytes
remain identical. 797TAP remains byte-identical to the original.

Original archives, commercial GLBs/textures/WAVs, imports and export binaries
remain outside Git. Git contains tools, compact IR/validation metadata, source
and supplied branding. A full private project snapshot includes restored assets;
the source/evidence ZIP excludes reusable commercial assets from its source tree.

Integration fixes are limited to explicit GDScript types, startup camera ordering,
null ambient-position fallback, UTF-8 subprocess/timeout/error handling, stable
import UIDs/line endings and rendering compatibility. Ambient source was disabled
and imported legacy materials defaulted to fully metallic, producing a black
viewport; explicit color ambient and nonmetallic imported materials restore
visibility. Shared imported material resources avoid stale override handles when
rooms are replaced rapidly. No puzzle, trigger, inventory or event semantics changed.

## Manual boundary

**G10 remains PENDING_MANUAL_USER; `demo-known-good-001` is not created or allowed.**
Follow `docs/KG001_MANUAL_SANITY_CHECKLIST.md` using the normal Windows application.
Automated audio events do not establish audible quality or original Miles parity.
Original framebuffer parity and forensic HOLDs remain unpromoted. The earlier
BLOCKED Windows artifact is superseded by the final Candidate 1 artifact.
