# OpenAzrael v87 — evidence-aware gameplay event graph

v87 begins moving the demo vertical slice away from room-specific hard-coded state changes into a small data-driven event layer.

## What changed

`data/gameplay_event_graph_v87.json` is the first executable gameplay IR for the demo. Each action carries its evidence confidence. `scripts/legacy_event_runner_v87.gd` executes only a deliberately small opcode set: state flags, puzzle nodes, inventory changes, and one-shot audio.

The R7 water-switchboard completion and the R8 lens placement / optical start / secret-door state / shield pickup now dispatch through named event graphs. Visual interpolation remains in the room interaction scripts because exact original timing and some movement semantics are still HOLD.

## Why this matters

The long-term importer can translate recovered PUZZLES.DAT / OBJECTS.DAT operations into the same IR instead of accumulating one-off GDScript. Classic mode can preserve provenance and confidence per action, while later enhanced/remastered presentation can react to the same canonical gameplay state.

## Evidence boundary

This is an architecture/generalization milestone, not a claim that every reconstructed action is original. `R8Counter` opcode 0x0e remains UNKNOWN. R8 timer duration and DoorR8 rotation/timing remain HOLD. Inventory IDs and `demo_complete` are OpenAzrael reconstruction state. Verified/high-confidence sound and state associations retain those labels in the graph.
