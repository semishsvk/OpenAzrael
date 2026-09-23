# Remaster Framework tooling foundation

This directory is the shared, source-safe foundation for OpenAzrael tooling and
future remaster projects.

## Goals

- keep original game data immutable;
- give every tool a machine-readable contract;
- separate game-specific extraction from reusable validation and asset tooling;
- make deterministic outputs the default where practical;
- allow existing OpenAzrael scripts to be migrated gradually instead of rewritten;
- provide a future path for OpenCadaver and other projects.

## Tool families

1. Data Lab
2. Texture Lab
3. Audio Lab
4. Localization Lab
5. Validation Lab
6. Project / Release Tooling

The registry intentionally starts by wrapping existing proven scripts. New tools
should register in `tool_manifest.json` before they become dependencies of other
framework components.

## CLI

From the repository root:

    python -m tools.remaster_framework.cli validate
    python -m tools.remaster_framework.cli list
    python -m tools.remaster_framework.cli list --family data_lab
    python -m tools.remaster_framework.cli show source_safe_inventory
    python -m tools.remaster_framework.cli inventory PATH --output inventory.json
    python -m tools.remaster_framework.cli discover-corpus PATH --output corpus.json
    python -m tools.remaster_framework.cli catalog data --output artifacts.json
    python -m tools.remaster_framework.cli verify-catalog data --manifest artifacts.json

The inventory, discovery, and catalog operations are read-only with respect to
the scanned corpus. Explicit output manifests are excluded where necessary so
repeated runs over unchanged input remain stable.

OpenAzrael-specific adapters are kept outside the reusable core under
`tools/openazrael_adapters/`.

## Migration rule

Do not rename or delete legacy versioned scripts merely to fit this framework.
Register them first, characterize their inputs/outputs with tests, then migrate
shared logic into stable modules only when parity has been proven.

## Verify / Release orchestration

OpenAzrael uses a thin project profile over the reusable `verify_orchestrator.py`
core. FAST selects diff-matched gates and escalates unknown critical changes;
VERIFY runs the complete source-safe release set without creating a Candidate
build. See `docs/VERIFY_RELEASE_ORCHESTRATOR.md`.
