# OpenAzrael Roadmap

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

**Canonical checkpoint:** `v116-context-v32`  
**Technical base:** `openazrael_godot_poc_v116`

## Now — Candidate 3 source and runtime gate

1. Require the Candidate 3 source workflow to PASS on Python 3.11 and 3.12 at the exact intended build SHA.
2. Restore the local R1/R7/R8, audio and 86-texture Classic corpus and run `tools/run_candidate3_preflight.py`.
3. Require v109/v110/v111/audio-v116/physical-v117/well-tongs-v118 literal PASS. For traversal, require natural R1/R7/R8 support plus both real R8 stair profiles up/down; retain the v117 step-debug trace on failure.
4. Require Issue #11 color-key validation plus the KEYHOLE# vertical-orientation regression; TONG6/MINETON# is the negative control and must not receive the keyhole-only UV correction.
5. Export only through `tools/export_candidate3.py`. Reject changed HEAD, dirty Git, changed evidence/Godot, any runtime asset mutation/addition/removal, or failed exported startup smoke.
6. Perform receipt-bound G10 on the exact EXE/PCK pair: floor, stairs, well+tongs, audible triggered/ambient audio, transparency, upright keyhole, full route, save/load and F11.
7. Keep `demo-known-good-001` forbidden until all G00-G10 gates are literal PASS with zero release blockers and zero reproducible softlocks.

## Then — freeze the first known-good demo baseline

1. Record the passing Candidate 3 commit, Godot version, preflight/export receipts and artifact hashes.
2. Close only blockers actually demonstrated fixed by exact-candidate automated + manual evidence.
3. Create `demo-known-good-001` only if the accepted KG-001 release rule is satisfied; never rewrite the tag later.
4. Preserve Candidate 2 Windows evidence as historical, not current, runtime evidence.

## Next — after Candidate 3 validation

### Localization implementation
Architecture is approved in `docs/LOCALIZATION_ARCHITECTURE.md`, but runtime implementation waits until after the first clean Candidate 3 runtime/manual cycle.

1. Define String IR and immutable semantic-ID conventions.
2. Generate the built-in English fallback catalog and `openazrael.pot`.
3. Add POT/PO tooling, glossary workflow and missing/duplicate-ID validators.
4. Implement `LocalizationManager` with manifest validation and non-overriding external PCK mounting.
5. Add pseudolocalization, overflow and Unicode/font coverage tests.
6. Build a small Slovak smoke-test pack.
7. Migrate demo-facing strings away from hard-coded user-visible text.
8. Feed the separately prepared Slovak translation corpus into the approved runtime pack format.

### Deferred forensic v117
- Audit generic/exact 27-byte copy classes and variable/generic allocation paths.
- Audit plausible stores into WORLD action-record +17..+26.
- Strengthen indirect/computed reachability evidence for the paired WORLD writer only where static evidence supports it.
- Preserve `PUZZLES_WORLD_AUTHORING_PRODUCER_EDGE` and `WORLD_WRITER_INDIRECT_REACHABILITY` as HOLD unless direct evidence changes them.

## Later
- Close remaining demo timing/motion semantics where recoverable.
- Obtain genuine original-runtime Classic audio parity evidence.
- Widen validated import/runtime coverage from the demo slice into retail rooms/data.
- Generalize import/runtime interfaces for full-game loading.
- Keep Classic / Enhanced / Remastered presentation modes on shared gameplay/world IR.
- Expand external language packs beyond the Slovak smoke-test path.

## Invariants
- Development order remains `DEMO -> faithful reconstruction -> validation -> generalization -> full game`.
- Git remains source history, not commercial-data backup.
- Original/commercial payloads remain outside normal Git history.
- Passing KG-001 validates the defined demo gates only; it does not automatically promote forensic HOLDs.
