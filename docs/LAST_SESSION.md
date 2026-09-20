# OpenAzrael Last Session

## Candidate 2 Windows execution — 2026-09-20

**KG-001 Candidate 2 / v116-context-v32: G00-G09 PASS; G10 PENDING_MANUAL_USER.**
Tested source `89ccf775dfd6abc21e6bc69f344fe2d349b4dd70`, Godot `4.7.2.stable.official.ed1daf0bf`.
The clean-checkout suite passed source validation, asset import, v109, v110,
v111 and audio-v116 (62 checks). The exported Windows EXE passed headless and
graphical smoke tests. Instrumented exported-PCK checks passed real floor
support in R1/R7/R8, nonzero Master audio output, cutout materials and F11 ZIP
capture without a gameplay-state hash change. Supplied Sigil icons are verified
inside the executable. Some headless scene tests report non-fatal ObjectDB
cleanup warnings; there are no ERROR or SCRIPT ERROR lines in the passing runs.

Additional integration fixes preserve the authored invisible R8/Object01
entrance support collision, repair empty ambient WAV loop ranges, and retain
Godot numeric typing and runner error handling. The v32 indexed palette rule
preserves the single near-magenta non-key pixel in BLOOS4#.

Candidate 1 manual failure remains historical evidence. Issues #6, #9 and #11
await human retest and remain release blockers. No `demo-known-good-001` tag
is allowed or created. Original Miles parity and complete original renderer
transparency semantics remain HOLD. See `docs/CANDIDATE2_WINDOWS.md` and
`data/tests/kg001_candidate2_windows.json` for details.

## Source and artifacts

- Branch: `build/kg001-candidate2-windows`.
- Integrated main: `356dddf71163b99539badb571cce500f99835acc`.
- Integrated PR #10 head: `1342e461c0d5d0c07034b0fc8f42a1eb77510c98`.
- Tested runtime: `89ccf775dfd6abc21e6bc69f344fe2d349b4dd70`. Later changes are documentation and evidence only.
- Windows: `OpenAzrael-KG001-Candidate2-v116-context-v32-Windows.zip`.
- Evidence/source: `OpenAzrael-KG001-Candidate2-v116-context-v32-evidence.zip`.
- Full private snapshot: release tier, label `KG001-Candidate2-v32-G10-pending`,
  generated and verified by the canonical snapshot tools; identifiers are in
  the output release manifest. Commercial data stays outside Git.

## Next action

Run the exported build, manually retest floor support, audibility and cutouts
(Issues #6/#9/#11), then finish the complete production-interaction demo route.
Use F11 to collect any bug report. Record G10 explicitly; do not infer PASS from
automation. Localization and the v117 forensic work remain deferred.
