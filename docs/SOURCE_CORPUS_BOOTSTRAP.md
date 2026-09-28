# Persistent source corpus bootstrap

OpenAzrael keeps commercial game payloads outside Git, but their identity and
location must not be rediscovered for every build or validation session.

The source registry provides one persistent, fail-closed entry point for both
the official demo corpus and the retail game corpus.

## Private source home

The default private state directory is:

```
~/.openazrael/sources
```

Override it with a durable local/private path when required:

```bash
export OPENAZRAEL_SOURCE_HOME=/path/to/private/openazrael-sources
```

The directory contains the local registry, optional private mirrors,
materialized archives and full SHA-256 inventory manifests. It is explicitly
Git-ignored and MUST NOT be committed.

For ephemeral CI/Work containers, point `OPENAZRAEL_SOURCE_HOME` at a durable
mounted private volume when one is available. The repository stores identity
contracts, never the commercial bytes.

## Demo / ATDEMO

The canonical official-demo archive identity is source-backed by
`data/tests/kg001_colorkey_corpus_audit_v116.json`:

- file: `atdemo.zip`
- bytes: `5,243,364`
- SHA-256:
  `bf0c87f731bb4e8767d86adcdbd4e6539b1cb9300131b34ac68dac5e587e7652`

Register it once:

```bash
python tools/bootstrap_openazrael_sources.py register demo /private/atdemo.zip --mirror
```

`--mirror` is recommended for the demo because the archive is small. It copies
the canonical archive into the private source home so the original download
location may disappear without breaking future builds.

An already extracted ATDEMO directory may also be registered. In that case the
complete deterministic directory inventory is pinned locally.

Verify later without rediscovery:

```bash
python tools/bootstrap_openazrael_sources.py verify demo
```

Resolve/materialize it and rebuild ignored runtime assets:

```bash
python tools/bootstrap_openazrael_sources.py prepare demo --restore-demo-runtime
```

`tools/restore_candidate_assets.py` now also resolves the registered demo
automatically when no positional path is supplied.

The canonical demo root is anchored by `PUZZLES.DAT`, `ROOMS.DAT`, `WORLD.DAT`, `MUSIC.DAT`, `R.EXE` and `CHARACTE.DAT`, plus the existing texture/audio counts. The official demo does **not** contain `OBJECTS.DAT`; that remains a retail-only corpus anchor.

## Retail

Retail is deliberately stricter about claims. The repository has
evidence-backed anchors for the retail corpus, but does not invent a universal
retail SHA-256 before the user's actual canonical retail installation/extraction
is mounted.

Required registration anchors are currently:

- `PUZZLES.DAT`
- `OBJECTS.DAT`
- `ROOMS.DAT`
- `CHARACTE.DAT`

Additional forensic/localization evidence may include `NIAMH.DAT`,
`CON*.DAT`, `*.ANI` and `RANIM*.ANM`.

Register the canonical extracted retail root once:

```bash
python tools/bootstrap_openazrael_sources.py register retail /private/azraels-tear-retail
```

This computes a deterministic SHA-256 inventory of every file and pins that
inventory in the private registry. Every later full verification must match the
same inventory exactly:

```bash
python tools/bootstrap_openazrael_sources.py verify retail
```

For a stable installation path, reference mode is sufficient. To make a private
copy inside the source home, use `--mirror`; this may require substantial disk
space.

Resolve the verified retail root for localization/forensics:

```bash
python tools/bootstrap_openazrael_sources.py prepare retail
```

The resulting local binding is written to:

```
.tmp/openazrael_sources.json
```

Future retail tools should call the shared
`tools.remaster_framework.source_registry.resolve_source("retail")` helper
instead of scanning disks or guessing paths.

## Normal build flow

Once registered, the intended workflow is:

```text
register once
    ↓
verify / prepare
    ↓
asset restore
    ↓
VERIFY
    ↓
CANDIDATE
```

Candidate 3 and Candidate 4 preflights now auto-resolve the registered demo
corpus when a demo path is not supplied.

Candidate 4 therefore supports:

```bash
python tools/run_candidate4_preflight.py \
  --godot /path/to/godot \
  --soundfont /path/to/soundfont.sf2
```

without `--demo-dir`, provided the demo corpus was registered previously.

## Source-safety rules

The following are allowed in Git:

- source corpus contracts;
- SHA-256 fingerprints;
- counts and byte sizes;
- source-safe validation metadata;
- tools and tests.

The following remain private and Git-ignored:

- ATDEMO payload;
- retail binaries;
- mirrored private bundles;
- the local source registry;
- materialized commercial assets.

A missing source, changed hash, changed retail inventory or corpus-shape
mismatch is a hard failure. The toolchain must never silently search for a
different corpus and continue.
