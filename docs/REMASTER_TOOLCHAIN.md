# OpenAzrael reusable remaster toolchain

Status: POC foundation started on tooling/remaster-framework-poc-01.

## Architecture

The intended reusable flow is:

Original game data
-> source-safe inventory and provenance
-> game-specific extraction / forensics
-> normalized intermediate representation
-> validators and graph analysis
-> engine adapter / Godot runtime
-> physical-player validation
-> evidence capture
-> KG/release gates

Asset-side labs consume the same provenance and normalized metadata:

- Texture Lab
- Audio Lab
- Localization Lab

## Phase 0 - foundation

Implemented in the first POC:

- common ToolContract;
- six stable tool-family identifiers;
- machine-readable tool registry;
- registry validation;
- CLI for listing and inspecting contracts;
- deterministic source-safe SHA-256 inventory;
- tests covering deterministic inventory and registry integrity.

Existing tools are registered rather than renamed, so this branch does not alter
runtime behavior or invalidate historical investigation artifacts.

## Phase 1 - Data Lab adapters

Next safe targets:

- register the remaining extraction and forensics scripts;
- define a common ArtifactManifest and ProvenanceRecord schema;
- add adapters for demo/retail corpus discovery;
- establish normalized IR schema/version metadata;
- add graph export for room, puzzle, trigger, and asset references.

## Phase 2 - Validation Lab

Build the reusable PPPV layer around the current physical-traversal work:

- PlayerDriver interface;
- Action and Observation contracts;
- TriggerContract;
- RuntimeEvidence record;
- before/after canonical state hashing;
- physical traversal assertions for floor, stairs, portals, and interactions;
- golden puzzle scenario: Tongs -> Well;
- reusable full-playthrough scenario format.

The critical rule is that a puzzle test must prove observable runtime effects,
not merely call puzzle logic directly.

## Phase 3 - Labs

Texture Lab:
- source inventory adapter;
- decode/upscale/recreate stages;
- alpha/colorkey validation;
- visual review packs and approvals.

Audio Lab:
- inventory and reference audit;
- waveform/spectrogram QA;
- logical Audio Map;
- event/emitter mapping;
- parity and spatial-runtime evidence.

Localization Lab:
- source string extraction;
- semantic IDs and glossary;
- PO/POT workflow;
- external language-pack builder and compatibility manifest.

## Phase 4 - Project and release tooling

- context/document consistency validator;
- build provenance manifest;
- fresh-checkout verification;
- KG gate aggregator;
- bug-report evidence bundle integration;
- version/build/KG metadata unification.

## Phase 5 - extraction into a generic framework

Only after OpenAzrael proves the interfaces in production should generic modules
be extracted for reuse by OpenCadaver. Game-specific parsers and runtime adapters
remain outside the shared core.

## Non-negotiable safety properties

- original source corpus is never modified;
- generated artifacts are written outside source roots or to explicit outputs;
- deterministic tools have regression tests;
- runtime-changing tools must never be mislabeled source-safe;
- framework adoption must not require rewriting already validated legacy tools;
- migration happens through adapters plus parity tests.
