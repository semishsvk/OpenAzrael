# PUZZLES alternative direct-open audit — v105

## Result

v103/v104 close the obvious direct standard-stdio route: all **47/47** audited
direct `fopen` call sites are classified and **0** remain plausible direct
PUZZLES.DAT candidates.

v105 extends that bounded negative search to the other obvious direct-open
families used by the executable, including direct low-level/open-style and
audited DOS-style file-open routes. The retained canonical project state records
**0 direct PUZZLES open candidates** across those audited direct mechanisms.

This is the closure referred to by v106 when it says that v103–v105 exhausted
the obvious direct runtime-open routes before testing the competing WORLD.DAT
runtime-serialization hypothesis.

## Interpretation

Confidence is **HIGH for the audited direct mechanisms**. The result does not
establish that PUZZLES.DAT is unused and does not identify a runtime loader.

Still possible and explicitly outside the result:

- indirect calls to known wrappers;
- computed function-pointer dispatch;
- custom/resource/container abstractions;
- runtime-generated routing;
- authoring/export transformation into another runtime representation.

The PUZZLES runtime-access identity therefore remains **HOLD**.

## Next-step handoff

v106 follows the runtime side instead and verifies that WORLD.DAT is directly
loaded as a seven-section structured serialization that consumes
**96,425 / 96,425 bytes** exactly.

Provenance: compact source-safe retained summary reconstructed from canonical
v104, v106 and project-state evidence. No raw commercial-derived bytes are
included.
