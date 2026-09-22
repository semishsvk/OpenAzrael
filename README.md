# OpenAzrael

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

## Current status — Candidate 4 hardening

**Historical technical checkpoint:** `openazrael_godot_poc_v116` (internal provenance, not project version)  
**Runtime:** Godot 4  
**Active demo slice:** R1 -> R7 -> R8  
**Next build:** KG-001 Candidate 4  
**Source status:** Candidate 4 hard release contract PASS at source level  
**Runtime status:** NOT YET ELIGIBLE FOR EXPORT — exact-head asset-backed preflight still required  
**Known-good tag:** `demo-known-good-001` — NOT ALLOWED until all automated gates and G10 pass

### Candidate 4 release intent

Candidate 4 is the first build intended to be fully playable end to end, with zero
known critical bugs, zero reproducible softlocks, complete restored demo room
geometry, complete required audio, deterministic synthetic-player coverage and
a full manual G10 pass on the exact exported EXE/PCK pair.

The Candidate 4 gate requires the v117-v131 traversal/fidelity stack, PPPV v2,
the fail-closed room forensic report, and the canonical 30/30 WAV demo corpus.
The demo package also contains 24 XMI music assets; Candidate 4 is fail-closed
until route evidence proves either tested runtime support for the music required
by the accepted demo route or proves that XMI music is not used on that route.

### Immediate priority
1. Close the XMI route-usage question and implement/test required music playback if needed.
2. Restore the full canonical asset set from the official demo and run `python tools/run_candidate4_preflight.py --godot <Godot> --demo-dir <ATDEMO>`.
3. Require PASS for all inherited runtime gates, v117-v131 fidelity/geometry checks, 30/30 WAV validation and PPPV v2 repeated deterministic end-to-end playthroughs.
4. Export only through `python tools/export_candidate4.py --godot <Godot>`.
5. Complete G10 on that exact Candidate 4 EXE/PCK pair, including full traversal, all required transitions/puzzles, stairs, audio, visuals and save/load.

See `docs/CANDIDATE4_RELEASE_CRITERIA.md` and
`data/tests/kg001_candidate4_release_contract_v132.json`.

### Current architectural decisions
- Evidence-first flow remains `original data -> forensic/import tools -> OpenAzrael IR -> Godot runtime`.
- Candidate diagnostics are observational only; they do not directly mutate gameplay state.
- F11 captures a source-safe diagnostic ZIP for GitHub Issues; see `docs/BUG_REPORTING.md`.
- Localization architecture remains deferred until after the first clean Candidate 4 runtime/manual validation.
- Existing forensic HOLDs remain HOLD; documentation cleanup does not promote unresolved claims.

For canonical context start with `OPENAZRAEL_CONTEXT.md`, `docs/PROJECT_STATE.md`,
`docs/LAST_SESSION.md`, `docs/VERSIONING.md`, and `data/project_context.json`.
Internal `vNNN` labels are evidence/tool revisions, not the project version.

---

## Source and asset policy

OpenAzrael is an unofficial fan-remaster/reconstruction project. This repository is intended to contain OpenAzrael-authored source code, tooling, metadata, tests and documentation only.

Original Azrael's Tear commercial game payloads are **not distributed in Git**. Original audio, room geometry, textures, executables and data files must remain outside the repository and are restored locally only for validation/import workflows where the user is entitled to use them.

The project is not affiliated with or endorsed by the original game's rights holders. Existing forensic confidence/HOLD labels describe reconstruction evidence only; they do not transfer ownership of the original game's content.

Public-release safety details are tracked in `docs/PUBLIC_RELEASE_AUDIT.md`.
