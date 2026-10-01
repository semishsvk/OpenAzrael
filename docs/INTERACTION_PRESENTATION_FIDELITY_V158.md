# KG-001 Interaction Presentation Fidelity v158

## Problem

The current runtime can prove that an interaction changed canonical state while still failing to reproduce what the original player saw. Generic `pickup.gd` currently acquires the item, hides its world visual and frees the interaction area. That is correct state plumbing but not a complete fidelity contract for readable/inspectable objects.

## First vertical slice: R1 r1p1

Existing room reconstruction identifies `r1p1` as a `PAPER` family object and maps it to runtime item `parchment_r1`. Existing object-lifecycle work already establishes that it is visible in fresh R1 and removed from the authored location after pickup.

The source cursor corpus contains dedicated LOOK-family cursors in addition to TAKE/USE, so presentation/inspection is modeled separately from state mutation.

### Current evidence boundary

Supported:
- world object: `R1/r1p1`
- source family: `PAPER`
- canonical runtime item: `parchment_r1`
- pickup cursor: `TAKE`
- pickup changes canonical inventory
- authored world visual disappears after pickup

Not yet source-bound:
- exact readable image/text shown by the original
- exact trigger relationship between TAKE and first READ/LOOK presentation
- whether the parchment can be reopened from carried inventory
- exact close/advance input and cursor animation

Those unknowns are HOLDs. They must not be replaced by invented text, generic parchment artwork or modern modal UI.

## Runtime architecture

Interaction fidelity is split into two layers:

1. **canonical effect** — acquire/remove item, flags, puzzle nodes, save/load;
2. **presentation effect** — source-backed modal/inspect/read view, cursor state, audio/animation and return-to-world behavior.

An interaction is fidelity-complete only when both layers required by its object contract pass.

## Validation extension

PPPV must eventually observe the sequence:

`target acquired -> expected cursor -> interact -> canonical state delta -> expected presentation opens -> source-backed presentation identity -> expected close input -> presentation closes -> world control/cursor restored`.

This is intentionally stricter than checking only `DemoState.inventory` or flags.

## Next evidence tasks

1. Locate the exact r1p1 readable payload in the authoritative demo corpus and/or executable references.
2. Trace PAPER/r1p1 references through ROOMS/WORLD/PUZZLES/action records.
3. Associate any source PCX/bitmap/text payload with hashes and provenance.
4. Determine TAKE -> READ/LOOK sequencing and close semantics from executable/data evidence.
5. Only then bind the payload into the runtime presentation layer.
6. Extend the same matrix to every demo object with LOOK/READ/PHOTO or multi-stage USE behavior.
