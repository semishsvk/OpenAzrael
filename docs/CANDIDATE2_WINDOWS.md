# KG-001 Candidate 2 / v116-context-v32 â€” Windows

This build combines main `356dddf71163b99539badb571cce500f99835acc`
with the reviewed source of PR #10 at
`1342e461c0d5d0c07034b0fc8f42a1eb77510c98`. It includes the floor collision
repair, physical audio routing, audited indexed source-palette transparency,
and F11 bug-report capture. The supplied Sigil artwork is embedded in Windows
executable resources and configured as the Godot application icon.

Additional integration repairs in this build:

- The v32 multiroom test exposed the missing R8 entrance support: the authored
  `Object01` horizontal quad (y=-87.124) bridges `tunnel07` and `step011` but
  was excluded with all TRANSPARANT surfaces. It now remains invisible while
  supplying collision. Trigger metadata, puzzle state and portal locations are
  unchanged. Regression verifies hidden rendering, collision and grounded feet.
- Floor tests use a four-unit drop and require arrival at the probed floor;
  the previous sixty-unit drop could place the capsule through a low ceiling.

- Explicit numeric types prevent Godot parser errors in trigger bounds and F11.
- Imported ambient WAV streams with an empty loop range now loop their decoded
  sample length. This also covers QOA imports; authored nonempty ranges remain
  unchanged. Merely observing `playing=true` did not detect this silent-loop bug.
- The audio regression checks nonempty forward loops on all seven emitters.
  Its physical event scenario now uses the actual S152V2 graph
  `R7_WATER_SWITCHBOARD_SOLVED`; gameplay event IR is unchanged.
- The headless test waits for mixer cleanup before shutdown.
- Validation records the tested commit, rejects engine errors and timeouts,
  returns failure for failed import/runtime checks, and cannot promote stale
  skipped results. Context promotion requires complete matching evidence.
- Tracked script UIDs and a source-safe Windows export preset support a clean
  checkout. Commercial room, texture, and audio data remain ignored.

Rebuild using `tools/restore_candidate_assets.py` against the local ATDEMO
directory, then `tools/run_kg001_candidate_v112.py --fresh-checkout
--promote-results --godot <Godot console executable>`. Use export preset
`Windows Candidate 2` with matching Windows export templates.

## Recorded result â€” 2026-09-20

Tested source: `89ccf775dfd6abc21e6bc69f344fe2d349b4dd70` on
`build/kg001-candidate2-windows`, using Godot 4.7.2.

- G00-G09: PASS, including the fresh-checkout import and evidence promotion.
- v109, v110, v111 and audio-v116: PASS; audio-v116 completed 62 checks.
- Rebuilt 86-texture corpus, legacy color-key masks and GLB materials: PASS.
- Exported Windows EXE headless and graphical smoke: PASS.
- Instrumented exported-PCK R1/R7/R8 entry floor support, cutouts, F11 capture and nonzero
  audio mix: PASS. This is automated rendering/mixer evidence, not a human playthrough.

Artifacts: `OpenAzrael-KG001-Candidate2-v116-context-v32-Windows.zip` and
`OpenAzrael-KG001-Candidate2-v116-context-v32-evidence.zip`.
Extract the entire Windows ZIP and keep the EXE and PCK together.

G10 remains a human test of the exported application, including floor support,
audibility, transparent surfaces, interactions and the complete demo route.
Issues #6, #9 and #11 remain release blockers until this manual retest is recorded.
Do not create `demo-known-good-001` from automated results alone. Original
Miles parity and complete original transparency semantics remain HOLD.
