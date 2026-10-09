# GitHub synchronization scope

The GitHub mirror is intentionally a source-and-context repository, not a redistribution archive of Azrael's Tear data.

Tracked in the GitHub baseline:
- implementation and reverse-engineering tools (`tools/**/*.py`),
- Godot runtime/project source (`*.gd`, `*.tscn`, `*.godot`, `*.tres`),
- canonical project context and Git/backup policy,
- the latest high-value forensic notes required to interpret current v107 state,
- machine-readable project/evidence/fingerprint registries,
- compact runtime IR/evidence metadata required by source code, including `data/gameplay_event_graph_v87.json` and `data/xaf_trigger_evidence.json`.

Kept outside GitHub and preserved in verified Library/off-site checkpoints:
- original commercial game data and audio,
- decoded/exported assets derived directly from commercial data,
- large reproducible forensic JSON/table dumps,
- milestone ZIPs and raw reverse-engineering dumps.

The excluded material is identified by SHA-256 manifests where practical. The canonical full checkpoint for this sync is `openazrael_godot_poc_v107` + `v107-context-v15`; GitHub is the versioned source mirror, not the sole disaster-recovery copy.

Additional v107 exclusion:
- `data/world_puzzle_sound_bridge_v107.json` is a reproducible forensic output containing commercial-derived raw record bytes/hex; keep it in verified checkpoints, not Git.

Compact numeric/name metadata needed by the clean runtime is allowed when it cannot reconstruct the excluded room/audio/texture payloads by itself. The underlying commercial-derived GLB/audio/texture assets remain outside Git.
