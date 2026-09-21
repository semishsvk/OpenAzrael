# KG-001 Candidate 3 — pre-build and export gate

**Candidate 3 historical result: REJECTED (G10 critical R1/Object02 floor collision).**  
The original Candidate 3 artifact must not be promoted or reused as Known-Good. Post-fix builds must additionally pass `r1_route_v119` and should use a new Candidate identifier.

Candidate 3 is fail-closed. A Windows export is allowed only after a complete
asset-backed KG-001 fresh-checkout run passes at the exact Git commit that will
be exported.

## 1. Source-only CI

GitHub Actions runs:

    python tools/run_kg001_candidate_v112.py --source-only

on Python 3.11 and 3.12. This layer is source-safe and does not require the
commercial demo assets. It validates repository tracking hygiene and the
source contracts, including v117 physical traversal, v118 well+tongs fidelity
and this Candidate 3 build guard.

## 2. Local asset restoration

If the ignored Candidate assets are not already restored:

    python tools/run_candidate3_preflight.py --demo-dir <ATDEMO> --godot <Godot>

The wrapper invokes the existing deterministic restore workflow. Restoration
may create ignored room/audio/texture files, but it must not change tracked
source. Any tracked change fails the preflight.

If assets are already restored:

    python tools/run_candidate3_preflight.py --godot <Godot>

## 3. Required runtime PASS set

The preflight runs the full fresh-checkout Candidate suite and requires literal
PASS for:

- v109 headless gameplay;
- v110 room/trigger regression;
- v111 full-demo synthetic playthrough;
- audio-v116;
- physical-traversal-v117;
- well-tongs-v118;
- r1-route-v119 (Candidate 3 R1/Object02 regression and audited R1 route traversal);
- collision-parity-v120 (generic visible floor-like mesh/runtime collision parity across R1/R7/R8).

It also requires a fresh Godot import, clean Git before/after, no forbidden
commercial payload tracked by Git, and the restored room assets to remain
Git-ignored.

A successful run writes:

    .tmp/kg001/candidate3_preflight_receipt.json

The receipt is bound to the exact Git HEAD, Godot version, candidate/fresh
evidence hashes and the complete restored runtime corpus under `assets/rooms`,
`assets/audio` and `assets/textures/classic` (including the canonical 86 Classic PNGs).

## 4. Guarded export

Export only through:

    python tools/export_candidate3.py --godot <Godot>

using preset `Windows Candidate 3`.

The exporter refuses to run if the source HEAD changed, Git became dirty,
the Godot version changed, the preflight evidence changed, any bound runtime
asset changed, **or the runtime asset path set changes at all**. Adding a new
Git-ignored room/audio/texture after preflight is therefore just as invalid as
mutating an existing file. Because Candidate 3 uses `embed_pck=false`, both the
EXE and PCK must be produced and shipped together.

After export, the wrapper launches the exported EXE in headless startup-smoke
mode and rejects non-zero exit status or Godot `ERROR:` / `SCRIPT ERROR:`
output. The export receipt is written only after this smoke passes. On success
it hashes both artifacts and writes:

    .tmp/kg001/candidate3_export_receipt.json

Do not bypass the wrapper with a direct editor export for a Candidate 3
artifact intended for KG-001 validation.

## 5. Post-export manual gate

The export is still **not KG-001**. G10 remains manual. Test in this order:

1. natural R1 spawn and sustained floor traversal;
2. both R8 stair profiles up and down;
3. R7 well+tongs interaction and audible 979TONGS event;
4. ambient and other triggered audio;
5. KEYHOLE#/TONG6 transparency **and correct upright KEYHOLE orientation**;
6. complete demo route and save/load sanity.

Only after G10 is recorded PASS and no release blocker remains may the
`demo-known-good-001` decision be considered.
