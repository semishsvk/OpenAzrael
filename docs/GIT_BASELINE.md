# OpenAzrael Git Baseline

Repository-safe baseline: **v106-context-v12**.

## Git contains
- Godot source/scenes/config;
- Python reverse-engineering/import/export/validation tools;
- documentation and context;
- compact evidence/IR JSON;
- SHA-256 manifests for excluded source/derived material.

## Git excludes
- `data/audio/original_audio/`, `data/*.DAT`, `assets/audio/`;
- derived room GLBs and Classic texture PNGs;
- executable/dump material;
- checkpoint ZIPs/backups/caches;
- multi-megabyte reproducible forensic indexes explicitly listed in `.gitignore`.

Recommended baseline commit: `sync: OpenAzrael v106 context v12`
Recommended tag: `v0.106-context`
