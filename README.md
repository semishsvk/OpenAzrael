# OpenAzrael

## Current status — v116-context-v26

**Technical base:** `openazrael_godot_poc_v116`
**Runtime:** Godot 4
**Active slice:** R1 -> R7 -> R8
**Current candidate:** KG-001 Candidate 1
**Candidate source status:** SOURCE_CONTRACT_PASS / source-ready
**Application watermark:** KG-001 Candidate 1 / v116-context-v24
**Godot runtime status:** G00-G09 PASS at recorded final source `6528d438ab2b14d344fb0e19f83ba5d5e699cd60`; Windows export and smoke PASS
**Manual status:** G10 PENDING_MANUAL_USER
**Known-good tag:** `demo-known-good-001` — NOT ALLOWED until G00-G10 all pass

### Immediate priority
1. Reuse the locally restored and ignored R1/R7/R8 room, texture and audio assets, or restore them reproducibly with `tools/restore_candidate_assets.py`.
2. The final fresh-checkout suite and Windows export are PASS; evidence names the tested source commit.
3. If G00-G09 are literal PASS, launch KG-001 Candidate 1 interactively and complete the G10 manual sanity route using F6/F7/F10 diagnostics as needed.
4. Only after the first clean Candidate 1 runtime/manual cycle begin the approved localization runtime implementation and resume deferred v117 forensic work.

### Current architectural decisions
- Evidence-first flow remains `original data -> forensic/import tools -> OpenAzrael IR -> Godot runtime`.
- Candidate diagnostics are observational only; they do not directly mutate gameplay state.
- Localization architecture is approved: stable semantic IDs, POT/PO authoring, built-in English fallback, external versioned PCK language packs, no core-resource replacement. Runtime implementation is deliberately deferred until after Candidate 1 validation.
- Existing forensic HOLDs remain HOLD; documentation cleanup does not promote any unresolved claim.

For canonical context start with `OPENAZRAEL_CONTEXT.md`, `docs/PROJECT_STATE.md`, `docs/LAST_SESSION.md`, and `data/project_context.json`.

See [Candidate 1 Windows integration](docs/CANDIDATE1_WINDOWS_ATTEMPT.md) for provenance and current build evidence.

Historical milestone notes, including the v105 source-safe summary, are preserved verbatim from main `92dc9089be0c71dd7177bcc433faa336c3a5a7e1` in [HISTORY_PRE_V116.md](docs/HISTORY_PRE_V116.md). Historical statuses are superseded by the current canonical context above.

---
