# OpenAzrael Backup & Versioning Policy

**Status:** CANONICAL  
**Introduced:** 2026-09-17  
**Applies to:** all OpenAzrael work after checkpoint `v44-context-v4`

## 1. Purpose
OpenAzrael uses two complementary systems:

1. **Git/GitHub** for source history, decisions, documentation, evidence metadata and reproducible tools.
2. **Full-project backups** for the complete working tree, including local original game data and other files intentionally excluded from Git.

Neither system replaces the other.

## 2. Git repository boundary
Track by default:
- Godot source and scenes;
- reverse-engineering/import/export tools;
- documentation and ADRs;
- machine-readable evidence and IR metadata;
- tests and validators;
- small derived artifacts that are useful for reproducibility.

Do **not** track by default:
- original commercial game payloads;
- CD/GOG/demo installation archives or disk images;
- raw extracted original audio/movie payloads;
- executable/dump material not explicitly cleared for repository storage;
- local caches, generated build/export output, and backup ZIPs.

`data/backup/source_fingerprints.json` records hashes of selected excluded source evidence so the exact local corpus can still be identified without committing the payload itself.

## 3. Branch policy
- `main`: only coherent, validated project checkpoints.
- `re/<topic>`: reverse-engineering experiments.
- `audio/<topic>`: audio reconstruction work.
- `graphics/<topic>`: presentation/remaster work.
- `gameplay/<topic>`: gameplay reconstruction work.
- `tooling/<topic>`: tooling/infrastructure work.

Experiments may be committed on topic branches while still `ANALYZED` or `TESTED`, but **must not be merged into canonical behavior as VERIFIED unless project evidence rules are satisfied**.

## 4. Commit policy
Create a commit after each coherent, reviewable unit of work. Preferred commit prefixes:

```text
re:       reverse-engineering evidence/tooling
audio:    audio reconstruction
runtime:  Godot/runtime behavior
tools:    import/export/validation tooling
docs:     documentation/context changes
test:     tests and validation
backup:   backup/versioning infrastructure
```

Examples:

```text
re: validate LE relocation candidate against entry-point invariants
audio: map R8 authored emitters into world IR
docs: update project state after v32 verification
backup: add snapshot integrity verification
```

## 5. Tag and release policy
Use annotated milestone tags for stable checkpoints:

```text
v0.44-context
v0.40
v0.40-demo-complete
```

A release checkpoint requires:
1. `python tools/validate_project_context.py` passes;
2. relevant domain tests pass;
3. `docs/PROJECT_STATE.md` and `docs/LAST_SESSION.md` are current;
4. unresolved claims remain marked HOLD/EXPERIMENTAL;
5. the repository has no accidental raw-source payloads staged;
6. a full snapshot has been created and checksum-verified.

## 6. Full backup policy
Full backups intentionally include files excluded from Git, except transient caches and previous backup archives.

Target retention policy:
- **daily:** 7 snapshots;
- **weekly:** 8 snapshots;
- **monthly:** 12 snapshots;
- **release:** retain all important releases unless deliberately archived elsewhere.

Use:

```bash
python tools/backup/create_snapshot.py --tier daily
python tools/backup/create_snapshot.py --tier weekly
python tools/backup/create_snapshot.py --tier monthly
python tools/backup/create_snapshot.py --tier release --label v0.44-context
```

Every snapshot produces:
- a ZIP archive;
- a `.sha256` checksum file;
- a JSON metadata manifest.

Verify with:

```bash
python tools/backup/verify_snapshot.py /path/to/OpenAzrael_....zip
```

## 7. 3-2-1 storage target
Maintain at least:
- working copy on the development machine;
- private GitHub repository for repository-safe content;
- automated off-site/cloud backup of the complete working tree;
- periodically disconnected external SSD snapshot.

The offline SSD is intentionally disconnected when not backing up.

## 8. Session-close rule
For a substantial session with intentional project changes:
1. update canonical context documents;
2. run project validation;
3. create a coherent local Git commit;
4. push to the private remote when configured/available;
5. for significant milestones, create and verify a full snapshot;
6. record the resulting commit/tag/snapshot identifiers in `docs/LAST_SESSION.md` when applicable.

A chat ZIP is a convenience checkpoint, **not** the sole backup or source-control history.

## 9. Security rule
Secrets, tokens, credentials, API keys, private keys and personal data do not belong in the repository or backup manifests. Credential stores should be managed by the operating system/provider, not copied into OpenAzrael source control.
