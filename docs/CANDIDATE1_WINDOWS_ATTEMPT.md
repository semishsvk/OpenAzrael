# KG-001 Candidate 1 / v116-context-v24 — Windows integration attempt

Date: 2026-09-19. Base main: `fb5a68a4f57c387cfc340997e3a9cf0191a481b6`.
Engine: Godot `4.7.2.stable.official.ed1daf0bf`.

## Result and boundary

The actual v109 run passes 13 checks, including the final canonical hash
`69cdb8287e548f7a31884e26c23b739ead10ed8f998318cd5690c0a3b03e7db8`
and the four-event audio oracle. All 31 GDScript resources load in a running
project with the real autoloads. This is not a completed playable build.

The Windows debug EXE/PCK export completed with exit code 0 and no export
errors. Its headless launch exits 2 with explicit missing R1/R7/R8 diagnostics.
The downloadable Windows artifact is therefore labelled **BLOCKED / NOT
PLAYABLE**; it is retained only as export and fail-fast evidence.

Final automated results: G00/G01/G02/G03/G07 PASS; G04/G05/G06/G08 remain
runtime-pending because v110/v111 are blocked. G09's fresh-checkout observation
has clean_before=true, clean_after=true, no forbidden tracked files and all
room paths ignored, but FAIL overall because required rooms/runtime runs are
absent. G10 remains manual pending. No known-good tag was created.

The local earlier retail prototype's GLBs are unsuitable for the canonical
demo: R1 has 67 primitives / 587 triangles instead of 69 / 593; R8 has 86 /
1048 instead of 87 / 1050. R7 has the expected 48 / 689, but all three GLBs
have zero embedded images. None were substituted into the candidate.

The eight locally available audio files exactly match the tracked source
fingerprints and were restored only under ignored `assets/audio/`. Godot's
import of original 797TAP.WAV reported a seek error. The local runtime copy now
has a terminal empty RIFF JUNK chunk; its format and all 5,079 PCM bytes are
identical. `tools/prepare_candidate_audio.py` reproduces this fix only from the
fingerprint-verified original. The original source is unchanged. The subsequent
audio import completed without engine errors.

Required remaining inputs: canonical demo R1/R7/R8 GLBs (or the original
demo XAF/AZF corpus to regenerate them), and the existing legacy ambient IR
`data/audio/legacy_world_ir.json`. The earlier local retail corpus is not an
equivalent replacement. Official Godot 4.7.2 Windows export templates have now
been downloaded, checked against ZIP member sizes/CRCs, fingerprinted and
installed in the discovered portable Godot installation.

## Integration fixes

- Explicit numeric/String/Dictionary declarations resolve GDScript inference
  errors. GraphicsMode's enum and autoload name collided in type annotations;
  the integer enum values are unchanged. No puzzle actions or semantics changed.
- Candidate commands have UTF-8 capture and a timeout. Nonzero exits or engine
  errors cannot pass merely because a PASS marker was printed. Blocked runs
  overwrite previous runtime evidence, preventing stale-result promotion.
- Context validation checks the retained v106 canonical summary and matching
  section-count/EOF metadata, plus the retained v105 README summary. The old
  validator required two files that have never been in this source mirror.
  This verifies source context, not a rerun of excluded binary forensics.
- A source-safe Windows x86_64 export preset includes runtime JSON explicitly
  and labels the executable Candidate 1. It contains no local asset payloads.
- Generated script UID metadata is retained for repeatable clean imports.

## Resume

Restore the matching local demo assets without adding them to Git. Resolve the
797TAP container via `tools/prepare_candidate_audio.py`, install matching Godot
Windows templates, then use a clean candidate checkout and run:

    python tools/run_kg001_candidate_v112.py --fresh-checkout --promote-results

Set `GODOT_BIN` to the discovered console executable. After all automated gates
pass, export `Windows Candidate 1` with `--export-debug` and test the exported
binary. Preserve the build, logs, fingerprints and source patch together.

G10 is **PENDING_MANUAL_USER**. Do not create `demo-known-good-001`.
