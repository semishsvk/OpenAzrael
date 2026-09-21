# OpenAzrael v112 — one-command KG-001 candidate runner

v112 is the established one-command KG-001 candidate workflow. The reusable
remaster framework now wraps this runner rather than replacing its historical
v109-v112 evidence formats.

## Default workflow

Run:

    python tools/run_kg001_candidate_v112.py

The source phase now executes:

- canonical project/context validation;
- the accepted KG-001 G00-G10 contract validator;
- remaster tool-registry validation;
- the complete source-safe remaster-framework unit suite;
- generic PPPV runtime-capability preflight;
- existing demo runtime IR / gameplay / state-space validators;
- v109/v110/v111 source contracts;
- v116 Candidate Diagnostics/F11 source contract;
- v117 physical traversal source contract;
- v118 Well+Tongs source/evidence contract.

The runner then discovers Godot from `--godot`, `GODOT_BIN`, `godot4`, or
`godot`, imports locally restored room assets when available, and executes the
existing v109/v110/v111 runtime runners plus the v117 physical traversal and
v118 Well+Tongs runtime regressions.

Temporary evidence remains under `.tmp/kg001/`.

## Fresh-checkout gate

For G09 use:

    python tools/run_kg001_candidate_v112.py --fresh-checkout

Fresh-checkout PASS still requires all of the original conditions simultaneously:

- clean Git worktree before the suite;
- clean Git worktree after the suite;
- no forbidden commercial/raw paths tracked by Git;
- all source validators PASS;
- Godot found;
- Godot room-asset import PASS;
- v109, v110, v111, v117 and v118 runtime status all PASS;
- R1/R7/R8 room assets present locally;
- those local room assets are ignored by Git.

The clean-after observation and `kg001_fresh_checkout.json` are written before
the reusable framework bundle or runtime metadata staging begins. Framework
generation therefore cannot retroactively turn a dirty checkout into G09 PASS.

## Reusable framework evidence

After the historical candidate evidence has been written, the runner generates:

- `kg001_release_gate_results.json` — SHA-256-bound G00-G10 mapping;
- `release_gate_summary.json` — BLOCKED or ELIGIBLE_FOR_KNOWN_GOOD;
- `pppv_coverage.json` — current physical-player gameplay coverage;
- `build_provenance.json` — candidate commit/engine/input identity;
- `kg001_framework_bundle.json` — compact index of the above.

A BLOCKED release summary is a valid framework output. For example, before G10
manual sanity exists, the framework bundle should succeed while Known-Good
eligibility remains false.

The release aggregator is fail-closed: defect inventory must be explicitly
complete. Missing manual defect review can never be interpreted as zero critical
bugs or zero softlocks.

## Staging metadata for the manual Candidate/F11 run

After G09 has been observed, optionally run:

    python tools/run_kg001_candidate_v112.py \
      --fresh-checkout \
      --stage-framework-metadata

This stages ignored, source-safe JSON under `data/runtime/`:

- `build_provenance.json`
- `release_gate_summary.json`
- `pppv_coverage.json`

A subsequent graphical Candidate run can include that exact build-level context
inside its F11 bug-report ZIP. Missing staged metadata does not disable F11.

## Promoting evidence

After verification, optionally use:

    python tools/run_kg001_candidate_v112.py \
      --fresh-checkout \
      --promote-results

In addition to the historical v109-v112 summaries, promotion copies v117/v118
runtime evidence and the reusable framework results into `data/tests/` for
review/commit.

Promotion occurs after the G09 clean-state observation, so the intentional dirty
state caused by committing evidence does not rewrite G09.

G10 manual sanity remains separate and cannot be auto-promoted by this tool.
Only explicit completed manual evidence can make the defect inventory complete
and satisfy G10.

## Failure behavior

A missing Godot binary, missing required room assets, failed historical source or
runtime validator, failed framework bundle generation, or failed requested
runtime-metadata staging returns a non-zero process status.

The runner never creates the `demo-known-good-001` tag. Tag creation remains an
explicit human/release action after the release summary is
`ELIGIBLE_FOR_KNOWN_GOOD`.
