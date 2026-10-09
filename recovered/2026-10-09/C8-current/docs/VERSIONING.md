# OpenAzrael versioning

OpenAzrael uses separate identifiers for project releases, integration candidates, test/evidence revisions and immutable known-good checkpoints. They must not be treated as interchangeable version numbers.

## Project release version

The public/project version uses semantic pre-1.0 form:

- `0.MAJOR.MINOR-dev` — active development line;
- `0.MAJOR.MINOR-rc.N` — distributable release candidate;
- `0.MAJOR.MINOR` — accepted pre-1.0 release.

A semantic project version is assigned explicitly. Do not infer it from an internal tool or evidence revision.

## KG-001 integration candidate

`Candidate 1`, `Candidate 2`, `Candidate 3`, ... identify successive KG-001 integration/evidence attempts. They are not semantic project versions.

The active integration target is Candidate 3. The branch `integration/kg001-candidate3-pppv-v2` layers PPPV v2 onto the current Candidate 3 runtime tree without renumbering the project.

## Internal revision IDs

Names such as `v109`, `v116`, `v117`, `v118`, `v119`, `v120` and historical `v30`, `v107`, etc. identify test, forensic, context or tooling revisions. They remain useful provenance labels but must never be presented as the OpenAzrael project version.

Likewise, labels such as `v116-context-v32` are retained historical checkpoint identifiers only.

## Known-good checkpoints

`demo-known-good-001` is an immutable acceptance checkpoint. It may be created only when the KG-001 contract is satisfied for one exact commit and all release blockers are clear. It is independent of semantic project version numbering.

## Build identity

Every candidate build must record at minimum:

- exact Git commit SHA;
- semantic project version, when one has been explicitly assigned;
- KG-001 Candidate number;
- relevant internal evidence/test revisions;
- Godot version;
- build/export receipt identity.

The Git SHA and acceptance receipts are authoritative when two human-readable labels appear ambiguous.
