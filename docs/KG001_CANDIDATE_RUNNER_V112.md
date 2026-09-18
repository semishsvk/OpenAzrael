# OpenAzrael v112 — one-command KG-001 candidate runner

v112 turns the prepared KG-001 layers into one reproducible candidate workflow.

## Default workflow

Run:

    python tools/run_kg001_candidate_v112.py

The tool executes the source/context validators, discovers Godot from --godot / GODOT_BIN / godot4 / godot, executes v109, imports restored room assets with Godot when present, and then executes v110/v111.

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
- v109, v110 and v111 runtime status all PASS;
- R1/R7/R8 room assets present locally;
- those local room assets are ignored by Git.

A missing Godot binary or missing room assets cannot accidentally become PASS.

## Promoting evidence

After a successful candidate run, optionally use:

    python tools/run_kg001_candidate_v112.py --fresh-checkout --promote-results

The tool records the clean-state G09 result first, then copies summarized runtime/source/fresh-checkout JSON into data/tests for review and commit. The promotion intentionally makes the source checkout dirty after the G09 observation; that does not rewrite the already-recorded clean_before/clean_after evidence.

G10 manual sanity remains separate and cannot be auto-promoted by this tool.
