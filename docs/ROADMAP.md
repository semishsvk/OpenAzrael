# OpenAzrael Roadmap

**Canonical checkpoint:** `v116-context-v31`  
**Technical base:** `openazrael_godot_poc_v116`

## Now — Candidate 2 blocker retest

1. Restore Candidate 2 room/audio/texture assets with the v30 source pipeline.
2. Require the v110 R1 physical floor-support regression for Issue #6 to PASS.
3. Require the audio-v116 regression for Issue #9 to PASS: physical WAV loading, R1/R7/R8 ambient counts 2/3/2, playing players and a non-muted Master bus.
4. Require the Issue #11 color-key validator to PASS, including the restored asset audit for the ten-name `#` class and R1 KEYHOLE#/TONG6 mappings.
5. Export and launch the graphical Candidate 2 build.
6. Manually confirm stable floor collision, actually audible R1 ambient audio, and correct transparent keyhole/tongs with no pink/magenta color-key background before attempting the full route.
7. Keep Issues #6/#9/#11 and `demo-known-good-001` blocked until automated and human retests pass.

## Then — resume Candidate 2 runtime cycle

1. Restore the locally ignored R1/R7/R8 GLBs, Classic textures and required Candidate 2 audio assets on a Godot-capable checkout.
2. Run `python tools/run_kg001_candidate_v112.py --fresh-checkout --promote-results`.
3. Review G00-G09 evidence using the v112 status tooling.
4. If G00-G09 are literal PASS, launch the normal graphical **KG-001 Candidate 2** build.
5. Manually traverse the full demo route with the v116 diagnostics: F6 trigger volumes, F7 Candidate HUD, F8 audio debug, F9 audio parity capture, F10 canonical state dump, and F11 source-safe bug capture when a defect is observed.
6. Complete G10 only after the interactive route is clean.
7. Keep `demo-known-good-001` forbidden until all G00-G10 are PASS, with zero known critical bugs and zero reproducible softlocks.

## Next — after Candidate 2 validation

### Localization implementation
Architecture is approved in `docs/LOCALIZATION_ARCHITECTURE.md`, but runtime implementation waits until after the first clean Candidate 2 runtime/manual cycle.

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
