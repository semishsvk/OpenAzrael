# KG-001 Interaction Presentation Fidelity v173

## Verified model

Readable/inspectable demo objects are no longer modeled as state-only generic pickups. R.EXE and serialized WORLD actions establish a generic carried-object/book subsystem.

The relevant dispatcher semantics are:

- `0x07` — remove/deactivate the WORLD object. The normal-object path marks object byte `+0x12 = 1`; when the action location matches the current location it invokes the scene-object removal helper.
- `0x08` — add the WORLD object index to the carried-object set and UI. The set helper deduplicates and appends, so display order is acquisition order.
- `0x09` — paired inverse of `0x08`: remove from carried set/UI.
- `0x21` — open the generic source-backed book view. It resolves `BOOKS/<object>.BOK`, then the descriptor-selected `TEXTURES/BOOKS/<prefix><page>.PCX`.

## Demo readable action groups

Serialized WORLD records preserve the original order:

- R1/r1p1: `07 -> 08 -> 21`
- R1/r3t1: `07 -> 08 -> 21`
- R7/r7p1: `08 -> 07 -> 21`
- R8/r8t3: `08 -> 07 -> 21`
- R8/r8t4: `08 -> 07 -> 21`

R1/r1p1 therefore does **not** remain in the world after inspection. The earlier v162/v165 non-pickup interpretation was falsified by executable control flow plus the serialized action records. Its source page remains `1_1_0.PCX`; the carried label in WORLD is `Page - Apr 1194`.

R3T1/R8T3/R8T4 have verified 640x480 source pages and the WORLD display label `Tapestry Piece`.

R7/r7p1 has verified carried/remove/book intent and SPAPER evidence, but the supplied ATDEMO corpus contains no R7P1.BOK/page. That presentation remains `SOURCE_INCOMPLETE`; no replacement art or text may be fabricated.

## Runtime architecture

The runtime preserves two coupled layers:

1. canonical state: world-object removal/deactivation and DemoState carried state;
2. presentation: source-backed book page, modal input guard, RMB close, and return to world.

The classic HUD now follows carried acquisition order rather than a fixed invented order, matching the append behavior of the original `0x08` set helper.

## Validation gate

Source invariants can validate bindings and ordering statically, but KG-001 does not receive a runtime PASS until a Godot-capable VERIFY worker executes the PPPV cases with restored source pages. Required observations include carried-state delta, world-object disappearance, presentation OPEN/CLOSED, source identity, RMB close, modal movement/interaction suppression, room reload persistence, and save/load persistence.
