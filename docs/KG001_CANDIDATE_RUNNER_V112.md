# OpenAzrael v112 — one-command KG-001 candidate runner

v112 turns the prepared KG-001 layers into one reproducible candidate workflow.

## Default workflow

Run:

    python tools/run_kg001_candidate_v112.py

The tool executes the source/context validators, validates the pinned toolchain, generates the source-safe build fingerprint manifest, discovers Godot from --godot / GODOT_BIN / godot4 / godot, executes v109, imports restored room assets with Godot when present, and then executes v110/v111 plus the audio-v116 physical playback-readiness regression. Source validation also includes the Issue #11 indexed color-key regression and automatically becomes asset-backed when restored Classic textures are present.

All temporary evidence goes under .tmp/kg001/, which is ignored by Git.

## Fresh-checkout gate

For G09 use:

    python tools/run_kg001_candidate_v112.py --fresh-checkout

Fresh-checkout PASS requires all of the following simultaneously:
- clean Git worktree before the suite;
- clean Git worktree after the suite;
- no forbidden commercial/raw paths tracked by Git;
- source validators PASS;
- Godot found;
- Godot room-asset import PASS;
- v109, v110, v111 and audio-v116 runtime status all PASS;
- R1/R7/R8 room assets present locally;
- those local room assets are ignored by Git.

A missing Godot binary or missing room assets cannot accidentally become PASS.

## Optional canonical graphical capture

Before G10, a restored graphical checkout can run the same suite plus canonical R1/R7/R8 screenshot evidence:

    python tools/run_kg001_candidate_v112.py --fresh-checkout --visual-capture

For evidence promotion:

    python tools/run_kg001_candidate_v112.py --fresh-checkout --visual-capture --promote-results

`--visual-capture` is deliberately optional and does not redefine G09. When requested, however, the overall command requires the graphical capture to PASS and exits nonzero if Godot/display/restored room+audio requirements are missing or the capture contract fails. The capture runner writes PNGs and a manifest under the Candidate run-scoped `user://openazrael_candidate2_runs/<run_id>/captures/` directory; the compact parsed result is written to `.tmp/kg001/kg001_visual_capture_v117.json` and can be promoted to `data/tests/kg001_visual_capture_runtime_v117.json`.

The PNG SHA-256 values are observational evidence for that run. They are not a cross-GPU/driver pixel-perfect oracle.

## Windows one-command handoff

On the intended local Windows development machine, the thin v117 wrapper preserves the canonical sequence without reimplementing any gameplay/test logic:

    pwsh tools/run_kg001_candidate2_windows_v117.ps1 \
      -DemoDir C:\path\to\ATDEMO \
      -Godot C:\path\to\Godot_v4.7.2-stable_win64.exe \
      -PromoteResults

The wrapper:
1. validates the exact pinned toolchain;
2. restores ignored Candidate room/audio/Classic texture assets from the supplied extracted demo directory;
3. runs the canonical v112 suite with `--fresh-checkout --visual-capture`;
4. optionally promotes compact runtime evidence;
5. exports the tracked `Windows Candidate 2` debug preset;
6. writes EXE/PCK SHA-256 metadata only to ignored `.tmp/kg001/kg001_windows_candidate2_export_v117.json`.

Use `-SkipRestore` only when the ignored Candidate assets have already been restored from the canonical corpus. Use `-SkipExport` when validating runtime/captures without building the Windows package. `-ValidateOnly` checks wrapper/source wiring without requiring local commercial assets.

## Promoting evidence

After a successful candidate run, optionally use:

    python tools/run_kg001_candidate_v112.py --fresh-checkout --promote-results

The tool records the clean-state G09 result first, then copies summarized v109/v110/v111/audio-v116 runtime/source/fresh-checkout JSON into data/tests for review and commit. The promotion intentionally makes the source checkout dirty after the G09 observation; that does not rewrite the already-recorded clean_before/clean_after evidence.

G10 manual sanity remains separate and cannot be auto-promoted by this tool.


## Physical audio boundary

The audio-v116 runner checks required WAV PCM non-silence when restored assets are present, Master-bus routing, recovered ambient emitters, a real Event-IR AudioStreamPlayer and nonzero frames/peak through a temporary Master-bus AudioEffectCapture. It does not prove speaker/headphone audibility or quality and does not prove original Miles pan/volume parity. G10 must still confirm that the user actually hears expected ambient and event audio.


## Legacy color-key boundary

Issue #11 is validated during the source phase. The validator exercises indexed palette-key semantics, fail-closed ambiguity, binary alpha, hidden-RGB edge bleed and a synthetic XAF->GLB MASK material. When the local Candidate corpus has been restored, the same command audits all 86 Classic PNGs, requires exactly one used indexed key for each of the ten `#` assets, and checks the R1 KEYHOLE#/TONG6 mappings. Final visual acceptance remains manual in G10; complete original transparency/blending semantics remain HOLD.
