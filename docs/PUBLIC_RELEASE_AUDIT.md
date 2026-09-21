# OpenAzrael public-release audit

**Audit date:** 2026-09-21  
**Canonical private repository:** `semishsvk/OpenAzrael`  
**Audited active branch:** `test/kg001-physical-traversal`

## Purpose

This audit determines whether OpenAzrael can be exposed publicly without publishing original Azrael's Tear commercial payloads, build artifacts, credentials, or avoidable local-machine information.

## Current-tree result

The active Candidate 3 tree is **source-safe for a public mirror** after the sanitization work recorded in this branch.

Observed controls:

- original/commercial payload roots are Git-ignored: `original/`, `raw/`, `source_original/`, `data/audio/original_audio/`, `assets/audio/`, `assets/rooms/`, and `assets/textures/classic/`;
- executable/dump/archive/build outputs are excluded;
- Candidate runtime assets remain local and ignored;
- no tracked WAV/AZF/XAF/DAT/EXE/PCK/archive payload was found in the active tree;
- no tracked file over 250 KiB was found on the audited branch tips;
- no credential-like filename such as `.env`, private-key files, token files, or certificate bundles was found on the audited branch tips;
- current/default source scans found no GitHub PAT, private-key, AWS access-key, Google API-key, or Slack-token pattern;
- local Windows executable/user-data paths previously stored in Candidate 2 evidence were sanitized;
- `tools/run_kg001_candidate_v112.py` now records executable basenames instead of full local Python/Godot paths;
- `tools/validate_public_release_safety.py` is part of the source gate and fails closed on forbidden commercial paths/extensions, credential-like filenames, oversized tracked files, secret patterns, or local home-directory paths.

## Branch-tip audit

All 18 repository branch tips were inspected. No branch tip contained tracked original audio/room/texture payloads, export/build artifacts, forbidden game-data file types, credential-like files, or tracked files larger than 250 KiB.

The audited branches include `main`, both historical Windows Candidate branches, audio branches, texture/remaster tooling branches, the Candidate 3 traversal branch, and both historical sync staging branches.

## Historical commercial-data path audit

GitHub history queries returned **zero commits** touching the canonical forbidden payload paths checked during the audit:

- `original`
- `raw`
- `source_original`
- `data/audio/original_audio`
- `assets/audio`
- `assets/rooms`
- `assets/textures/classic`
- `R.EXE`
- `data/WORLD.DAT`
- `data/PUZZLES.DAT`

This is strong evidence that the known commercial payload locations were never committed to the canonical history.

## Historical .sync bootstrap payload

The early `sync-v107-stage` history contains Base64 chunks under `.sync/`. They reconstruct a small `tar.xz` source snapshot and delta.

The one-shot sync workflow verified the archive hashes, extracted the payload, and then explicitly rejected the known commercial asset roots, `R.EXE`, DAT payloads, disk images, archives/dumps, and any resulting tracked file larger than 250 KiB before publishing the expanded source commit.

The successful expanded commit contains the reconstructed source/tooling/docs tree and not the forbidden payload roots. The historical `.sync/*.b64` chunks are therefore treated as source-snapshot transport data, not recovered commercial game assets.

## Privacy/history findings

The repository is **not privacy-clean enough for an in-place public visibility switch without an explicit decision**:

1. historical commit author/committer metadata includes a personal email address;
2. older Candidate 2 evidence commits contain local Windows user/home paths;
3. those paths are sanitized at the current head, but normal follow-up commits do not erase them from Git history.

Neither item is a game-asset leak or credential leak, but both become publicly searchable if the canonical repository is switched to public.

Rewriting the canonical history solely to remove these items is not recommended during KG-001 stabilization because it would change hundreds of commit SHAs and invalidate exact-SHA evidence references.

## Recommended publication model

**Preferred:** keep the canonical development repository private and publish a separate source-safe mirror generated from the sanitized current tree with fresh public history.

The public mirror should:

- contain only the source-safe tracked tree;
- carry the canonical private source SHA as provenance metadata;
- never receive ignored commercial assets or Candidate EXE/PCK output;
- run the standard source-only GitHub Actions gate on public GitHub-hosted runners;
- run `tools/validate_public_release_safety.py` before source validation;
- keep asset-backed Godot validation in the private/local pipeline;
- clearly state that original game assets are not distributed and must be supplied separately by the user where legally permitted.

This model preserves all canonical private evidence SHAs while avoiding publication of historical personal metadata.

## Remaining publication decision

No explicit repository software license is currently present. Before describing a public mirror as open-source or inviting external reuse/contributions, the project owner should choose the intended license for OpenAzrael-authored code and documentation.

## Evidence boundary

This audit is a repository/publication safety review, not legal advice and not a statement about ownership of the underlying Azrael's Tear intellectual property.

The connector-backed review covered all current branch tips, known forbidden historical paths, the source/bootstrap transport boundary, current source-secret patterns, and the active Candidate 3 diff. It is not a byte-for-byte secret scan of every historical blob. The recommended fresh-history public mirror removes that residual historical uncertainty by construction.
