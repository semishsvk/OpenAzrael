# OpenAzrael Session Protocol

## Start of session
1. Read `OPENAZRAEL_CONTEXT.md`.
2. Read `docs/PROJECT_STATE.md`.
3. Read `docs/DECISIONS.md`.
4. Read `docs/LAST_SESSION.md`.
5. Locate domain artifacts via `docs/ARTIFACT_INDEX.md`.
6. Read `docs/BACKUP_VERSIONING_POLICY.md` for repository/release/backup work.
7. Run `python tools/validate_project_context.py` before changing canonical state when practical.

## During session
- preserve original evidence separately from derived output;
- create reproducible tools for non-trivial extraction/forensics;
- record hashes/versions when source identity matters;
- mark every new claim with lifecycle + confidence + provenance;
- never replace a HOLD with a guess simply to make the POC look complete;
- when a reconstruction is necessary, label it and isolate it from source facts.

## End of session
Update:
1. `docs/PROJECT_STATE.md`
2. `docs/LAST_SESSION.md`
3. `docs/ARTIFACT_INDEX.md` for new canonical artifacts
4. `docs/TEST_MATRIX.md` if lifecycle/verification changed
5. `data/project_context.json` if active state changed
6. `data/evidence/evidence_registry.json` for new evidence claims/artifacts
7. relevant domain note(s)

Then run:

```bash
python tools/validate_project_context.py
```

The final handoff must contain an exact next action that another session can execute without reconstructing the previous conversation.

## Repository / backup close gate
After canonical validation passes:
1. review `git status` and confirm no raw/original payload is accidentally staged;
2. commit the coherent repository-safe change;
3. push when the private remote is configured/available;
4. for significant milestone/release checkpoints run `tools/backup/create_snapshot.py` and then `tools/backup/verify_snapshot.py`;
5. record commit/tag/snapshot identifiers in `docs/LAST_SESSION.md` when applicable.

Git history and full backups are deliberately separate layers. A successful Git push does not prove that Git-excluded original evidence is backed up.

