# OpenAzrael reusable remaster toolchain

Status: Phase 0 complete; Phase 1 Data Lab POC implemented on
`tooling/remaster-framework-poc-01`.

## Architecture

The intended reusable flow is:

Original game data
-> source-safe inventory and corpus discovery
-> game-specific extraction / forensics
-> artifact provenance catalog
-> normalized IR descriptors/adapters
-> deterministic reference graph
-> validators
-> engine adapter / Godot runtime
-> physical-player validation
-> evidence capture
-> KG/release gates

Asset-side labs consume the same provenance and normalized metadata:

- Texture Lab
- Audio Lab
- Localization Lab

## Phase 0 - foundation

Implemented:

- common `ToolContract`;
- six stable tool-family identifiers;
- machine-readable tool registry;
- registry validation;
- CLI for listing and inspecting contracts;
- deterministic source-safe SHA-256 inventory;
- isolated CI workflow and unit-test suite.

Existing tools are registered rather than renamed, so framework adoption does not
alter runtime behavior or invalidate historical investigation artifacts.

## Phase 1 - Data Lab adapters

Implemented POC components:

### Artifact and provenance contracts

`ArtifactRecord` and `ProvenanceRecord` provide deterministic metadata around
existing artifacts. The catalog records path, size, SHA-256, media type, declared
sources, and normalized IR metadata without rewriting the artifact.

The verifier checks:

- path containment below the declared root;
- unique artifact IDs and paths;
- file existence;
- size identity;
- SHA-256 identity.

### IR adapter layer

`IRDescriptor` provides a common schema ID, schema version, kind, adapter ID,
and legacy flag.

Current OpenAzrael formats are adapted rather than converted in place. This
includes:

- declared-schema IR such as `openazrael.legacy_world_ir`;
- legacy gameplay graph v87;
- numeric-schema XAF trigger evidence;
- audit, audio, project-context, and test-contract fallbacks.

### Corpus discovery

The corpus-profile mechanism is generic and data-driven. The first committed
profile is `openazrael_demo_v1`.

Its demo identification rules are based on evidence already present in the
project, including PUZZLES.DAT / OBJECTS.DAT anchors, legacy AMB/NPC inputs, and
the Audio Lab AL-POC-01 canonical 30-WAV demo corpus.

A retail profile is intentionally HOLD until canonical retail evidence provides
anchors/counts. The framework supports adding it without code changes; we do not
guess retail corpus identity.

### Reference graph

The reusable `ReferenceGraph` contract stores deterministic nodes and edges.

The OpenAzrael adapter currently connects:

- rooms;
- trigger volumes;
- portal views;
- room transitions;
- gameplay/puzzle graphs;
- state and inventory keys;
- evidence sources;
- referenced texture assets;
- referenced audio assets.

This makes cross-domain questions machine-queryable, for example:

- which puzzle graph plays a given WAV;
- which trigger enters a destination room;
- which portal references a texture;
- which state keys a puzzle mutates;
- which source evidence supports a gameplay graph.

### Data Lab commands

From repository root:

    python -m tools.remaster_framework.cli validate
    python -m tools.remaster_framework.cli inventory SOURCE --output inventory.json
    python -m tools.remaster_framework.cli discover-corpus SOURCE --output corpus.json
    python -m tools.remaster_framework.cli catalog data --output artifact_manifest.json
    python -m tools.remaster_framework.cli verify-catalog data --manifest artifact_manifest.json

OpenAzrael-specific reference graph:

    python -m tools.openazrael_adapters.reference_graph \
      --xaf data/xaf_trigger_evidence.json \
      --gameplay data/gameplay_event_graph_v87.json \
      --output openazrael_reference_graph.json

## Phase 1 remaining hardening

Before declaring Data Lab stable rather than POC:

- register more existing extractor/forensics scripts in the tool registry;
- ingest canonical retail corpus evidence and add a retail profile;
- add explicit graph relations for Audio Lab emitters/mappings when those
  branches are integrated;
- add artifact-level producer/tool-version metadata where the legacy output
  already proves it;
- run the catalog/reference graph against a recovered full retail corpus.

None of these block moving on to the Validation Lab interface design.

## Phase 2 - Validation Lab

Build the reusable PPPV layer around the current physical-traversal work:

- `PlayerDriver` interface;
- Action and Observation contracts;
- `TriggerContract`;
- `RuntimeEvidence` record;
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
