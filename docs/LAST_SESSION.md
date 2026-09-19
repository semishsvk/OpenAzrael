# OpenAzrael Last Session

Canonical checkpoint: **v116-context-v26**. Date: 2026-09-19.
Application watermark: **KG-001 Candidate 1 / v116-context-v24**.

## Completed

- Integrated current main `43637474b4bddc34fcf38355901352f505c0c2a4`; its v26 documentation/localization decisions remain intact. Historical README is retained in `docs/HISTORY_PRE_V116.md`.
- Restored canonical demo R1/R7/R8 GLBs, 86 textures, required WAVs and ambient IR from the supplied demo. Commercial assets remain Git-ignored. Supplied branding PNG/ICO is tracked.
- Fixed GDScript typing, startup ordering/null fallback, S137 RIFF padding, Classic material/ambient integration and deterministic restore/import metadata. No puzzle semantics were changed.
- Ran `python tools/run_kg001_candidate_v112.py --fresh-checkout --promote-results` at `6528d438ab2b14d344fb0e19f83ba5d5e699cd60`: source/import/v109/v110/v111/fresh PASS, clean before/after and no forbidden tracked files.
- G00-G09 PASS. v109 has 13 checks; v111 has 33 checks; their final hash and four logical audio events equal the v108 oracle.
- Exported Windows x86_64 with supplied icon. EXE headless and graphical smoke PASS; six standard embedded icon sizes match the source ICO exactly. Captured R1/R7/R8 from the exported PCK with the same Godot 4.7.2 engine.
- Deliverables: `OpenAzrael-KG001-Candidate1-Windows.zip`, `OpenAzrael-KG001-Candidate1-source-evidence.zip`, a complete private project snapshot, and SHA-256 manifests. ZIP members are integrity-verified.

## Boundary and next action

**G10 PENDING_MANUAL_USER. No `demo-known-good-001` tag was created or permitted.**
Run the normal graphical full-demo manual checklist, including movement, interaction, audio perception and save/load. Automated launches/captures do not replace it.
The v110 test process retains a nonfatal ObjectDB cleanup warning at exit; no ERROR/SCRIPT ERROR occurs in the final suite or export smoke.
Classic pixel-perfect framebuffer/original Miles parity and other forensic HOLDs remain unpromoted. Localization runtime and v117 are deferred until after the first runtime/manual cycle.

The final source snapshot adds only documentation/context and promoted evidence after the tested runtime commit. See `docs/CANDIDATE1_WINDOWS_ATTEMPT.md`.
