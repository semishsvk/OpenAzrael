# PUZZLES direct-fopen classification — v104

v104 takes the complete v103 direct `fopen` census and classifies **every one of the 47 call sites** using bound-code-local filename/format/diagnostic evidence.

## Result

**47/47 direct calls are accounted for; 0 remain plausible direct PUZZLES.DAT candidates.**

The families cover music tables, books/PCX, character flags, conversations, room animations, GIF/AZF, maps, MIDI config, ambient SND, credits, animation/character ANI, dead-character saves, NPC state files, XAF, HUD data, wire-scan/object descriptions, samples, font/PCX, music, object HUD, save slots/world state, Miles debug output, and Miles driver configuration.

Two formerly awkward mid-image call sites are now especially clean:

- `0x15188` formats **`npc%d.dat`**, opens it for writing, then feeds the handle to the `fprintf`-like helper at `0x2B74C`.
- `0x15566` formats **`npc%d.dat`**, opens it for reading, then feeds the handle to the `fscanf`-like helper at `0x2AA9D`.

This also explains the text layout of the demo `NPC*.DAT` files and removes those calls from PUZZLES consideration.

The `0x2A6B8` binary writer is also constrained: after opening with `wb`, it builds the canonical PCX header start (`0x0A`, version 5, encoding 1, 8 bpp), so it is an image writer rather than puzzle serialization.

## Evidence boundary

The direct standard-stdio path is now excluded at **HIGH** confidence as the source of the PUZZLES loader. This is not a claim that `PUZZLES.DAT` is unused. Remaining possibilities include:

- an **indirect call** to the stdio wrapper,
- another/custom open/read API,
- a resource/container abstraction,
- runtime-generated routing not visible as a direct filename/xref,
- or another transformation path.

The PUZZLES loader identity therefore remains **HOLD**. The next experiment should audit indirect/alternative file readers and correlate them against the already VERIFIED `FE + 128` / dominant 190-byte record grammar.
