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

## Current status — Candidate 3 + PPPV v2 integration

**Historical technical checkpoint:** `openazrael_godot_poc_v116` (internal provenance, not project version)  
**Runtime:** Godot 4  
**Active slice:** R1 -> R7 -> R8  
**Current candidate:** KG-001 Candidate 3 on `integration/kg001-candidate3-pppv-v2`  
**Candidate source status:** HARDENED_SOURCE / source CI + exact-SHA asset-backed preflight required  
**Historical Candidate 2 status:** automated Windows evidence PASS, subsequent manual traversal FAIL; evidence retained but stale for current source  
**Candidate 3 + PPPV v2 runtime status:** NOT EXECUTED AT CURRENT HEAD  
**Known-good tag:** `demo-known-good-001` — NOT ALLOWED until G00-G10 all pass

### Immediate priority
1. Require the Candidate 3 Python 3.11/3.12 source gate to PASS at the exact build SHA.
2. Restore the ignored Candidate room/audio/texture assets and run `python tools/run_candidate3_preflight.py --godot <Godot> [--demo-dir <ATDEMO>]`.
3. Require literal PASS for v109/v110/v111/audio-v116/physical-v117/well-tongs-v118/r1-route-v119/collision-parity-v120, then require PPPV v2 scenario-suite + integrity and two matching guarded chained playthroughs + determinism integrity. v117 retains the bounded stair step-debug trace.
4. Export only with `tools/export_candidate3.py`; the exporter rejects changed HEAD/evidence/Godot, mutations **or additions/removals** in the bound runtime asset set, and requires exported-EXE startup smoke before writing a PASS receipt.
5. Complete G10 on that exact EXE/PCK pair: R1 floor, both R8 stair profiles, well+tongs + triggered audio, ambient audio, color-key transparency, upright KEYHOLE orientation, full route and save/load. `demo-known-good-001` remains blocked until then.

### Current architectural decisions
- Evidence-first flow remains `original data -> forensic/import tools -> OpenAzrael IR -> Godot runtime`.
- Candidate diagnostics are observational only; they do not directly mutate gameplay state.
- F11 captures a source-safe diagnostic ZIP for GitHub Issues; see `docs/BUG_REPORTING.md`.
- Localization architecture is approved: stable semantic IDs, POT/PO authoring, built-in English fallback, external versioned PCK language packs, no core-resource replacement. Runtime implementation is deliberately deferred until after the first clean Candidate 3 runtime/manual validation.
- Existing forensic HOLDs remain HOLD; documentation cleanup does not promote any unresolved claim.

For canonical context start with `OPENAZRAEL_CONTEXT.md`, `docs/PROJECT_STATE.md`, `docs/LAST_SESSION.md`, `docs/VERSIONING.md`, and `data/project_context.json`. Internal `vNNN` labels are evidence/tool revisions, not the project version.

---

## Source and asset policy

OpenAzrael is an unofficial fan-remaster/reconstruction project. This repository is intended to contain OpenAzrael-authored source code, tooling, metadata, tests and documentation only.

Original Azrael's Tear commercial game payloads are **not distributed in Git**. Original audio, room geometry, textures, executables and data files must remain outside the repository and are restored locally only for validation/import workflows where the user is entitled to use them.

The project is not affiliated with or endorsed by the original game's rights holders. Existing forensic confidence/HOLD labels describe reconstruction evidence only; they do not transfer ownership of the original game's content.

Public-release safety details are tracked in `docs/PUBLIC_RELEASE_AUDIT.md`.
