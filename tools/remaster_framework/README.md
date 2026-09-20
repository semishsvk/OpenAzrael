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
should register in tool_manifest.json before they become dependencies of other
framework components.

## CLI

From the repository root:

    python -m tools.remaster_framework.cli validate
    python -m tools.remaster_framework.cli list
    python -m tools.remaster_framework.cli list --family validation_lab
    python -m tools.remaster_framework.cli show source_safe_inventory
    python -m tools.remaster_framework.cli inventory PATH --output manifest.json

The inventory command is read-only with respect to the scanned corpus. Its own
output file is excluded from the scan, so repeated runs over unchanged input are
stable.

## Migration rule

Do not rename or delete legacy versioned scripts merely to fit this framework.
Register them first, characterize their inputs/outputs with tests, then migrate
shared logic into stable modules only when parity has been proven.
