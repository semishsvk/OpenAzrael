# OpenAzrael v111 — KG-001 full synthetic demo runner

v111 prepares G08: a no-human-input R1 -> R7 -> R1 -> R8 playthrough that deliberately calls the production interaction scripts rather than directly injecting gameplay flags.

## Production path exercised

The runner performs:

`Tongs pickup -> Door 1 -> R1/R7 trigger -> Well Key -> lever/wheel/lever -> R7/R1 trigger -> Door 2 -> R1/R8 trigger -> drained-bath lens -> Bible lens placement -> zxplate optical activation -> secret door -> Shield`.

Interaction nodes are located by the same names created by `RoomManager` and their real `interact()` methods are called. Room changes still happen through the real trigger-processing path; the runner only teleports the player to evidence-backed trigger centroids and the authored R8 activation center.

The optical sequence uses the production `r8_bible_interaction.gd` coroutine and timing constants. `Engine.time_scale=100` accelerates the wait without bypassing the sequence; a 600-frame bound prevents an infinite test hang.

## Oracles

The runner verifies the final canonical persistent hash against the v108 exhaustive-model shortest-success hash:

`e266137c74746996608ffcdd165b6a1072e2c9f55833473546061ccac0e05902`

and the logical Event IR audio stream:

`979TONGS.WAV -> S152V2.WAV -> S137.WAV -> S121.WAV -> 799SECDR.WAV`.

The source-contract validator also rejects direct `state.set_flag(...)` or `state.set_puzzle_node(...)` injection in the runner.

## Execution

After local R1/R7/R8 restoration/import:

```bash
godot --headless --path . --import
godot --headless --path . --script res://scripts/kg001_full_demo_runner_v111.gd
```

Missing room resources return `BLOCKED_MISSING_ASSETS` (exit 2). Current repository status is **SOURCE_CONTRACT_PASS / GODOT_RUNTIME_NOT_EXECUTED**.

This synthetic runner validates gameplay integration, not player locomotion skill, ray-aim ergonomics, rendered visuals, real WAV playback, original motion timing or Classic spatial-audio parity. Those remain separate gates/boundaries.
