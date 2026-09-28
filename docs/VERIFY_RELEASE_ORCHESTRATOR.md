# OpenAzrael Verify / Release Orchestrator

`tools/run_verify_release_orchestrator.py` is the source-safe decision layer for
the approved OpenAzrael FAST -> VERIFY -> frozen Candidate workflow. It does not
run an asset-backed preflight and it never creates a Candidate build.

The reusable selection/cache logic lives in
`tools/remaster_framework/verify_orchestrator.py`; OpenAzrael-specific gate
mapping lives in `data/tests/openazrael_verify_release_profile_v1.json`.

## FAST

Use FAST for ordinary development changes:

    python tools/run_verify_release_orchestrator.py --mode fast --base <known-base>

FAST always runs the current-tree public-release safety check, then adds only
the source gates whose declared trigger patterns match the committed Git diff
plus staged, unstaged and untracked worktree changes. A critical
change under `scripts/`, `tools/`, `data/`, Godot scene/project files or GitHub
workflows that is not covered by a known mapping automatically escalates to the
broad `kg001_source_suite`. Unknown critical changes therefore fail safe instead
of silently receiving a tiny test set.

For review without execution:

    python tools/run_verify_release_orchestrator.py --mode plan --base <known-base>

## Cache

The cache is local and ignored under `.tmp/kg001/`. A PASS is reusable only when
the gate fingerprint is identical. The fingerprint binds:

- the exact command;
- the verify/release profile SHA-256;
- all tracked files declared as gate inputs, including size and SHA-256;
- Python implementation/version, relevant validator package versions, and basic platform identity.

FAIL results are never reused. `--no-cache` forces execution.

## VERIFY

Before an asset-backed Candidate 4 preflight, run:

    python tools/run_verify_release_orchestrator.py --mode verify --no-cache

VERIFY uses the broad source-only KG-001 suite plus Candidate 4 release/music,
XMIDI, v151 proof-capture and release-script compile gates. It does not call
Candidate 3/4 asset-backed preflight, freeze or export commands.

A successful local run deliberately reports:

`LOCAL_VERIFY_PASS_CI_CONFIRMATION_REQUIRED`

It must not be interpreted as exact-head CI evidence.

## Exact-head CI

`.github/workflows/openazrael-verify-release.yml` runs for pull-request events. Once this workflow is present on the repository default branch, it can also be manually dispatched for an explicit SHA. It checks out that exact SHA, requires a clean
tree, runs uncached VERIFY first on Python 3.11 and then on Python 3.12, and
uploads both receipts.

Only the final 3.12 step is allowed to set the completed CI context after the
3.11 step has already passed. The orchestrator then requires the exact checked
out SHA before it can report:

`SOURCE_CHECKPOINT_READY_FOR_ASSET_PREFLIGHT`

This means source verification is ready for the next release stage. It is not
asset-backed runtime PASS, packaged/export PASS, G10 PASS or Known Good.

## Release continuation

After exact-head source readiness:

1. run the private Candidate 4 asset-backed preflight on that same SHA;
2. if and only if it passes, run `tools/freeze_candidate4_release.py`;
3. export only through the guarded Candidate 4 exporter;
4. run packaged checks and manual G10 on that exact EXE/PCK pair.

Candidate build creation remains outside this orchestrator by design.
