# OpenAzrael v107 — WORLD / PUZZLES sound-action bridge

## Result

v106 proved that the demo runtime directly loads `WORLD.DAT` and reconstructs a seven-section runtime object database. Its proposed next step was to follow the paired WORLD writer and use that caller lineage to look for an authoring/export path.

v107 tests that premise first. The paired writer at object1 `0x364A8` is real: it opens `world.dat` as `wb` and serializes the same global section families. However, in the bound demo executable it has:

- **0 direct rel32 CALL references**,
- **0 direct rel32 near-JMP references**, and
- **0 canonical LE fixup references** targeting the function entry.

This is a correction to the v106 next-step assumption. The writer remains a valid serializer counterpart, but it cannot currently establish a live producer/caller lineage. Computed or otherwise indirect invocation is not excluded, so total runtime reachability remains **HOLD**.

The live read side is different. `WORLD.DAT` reader `0x36638` has one exact direct caller at `0x1AAED`; its enclosing routine begins at `0x1AA78` and itself has a direct caller at `0x349E`. The same initialization sequence invokes the `SGDNAME.DAT` loader (`0x36414`) immediately before the WORLD reader. The runtime/startup role of the read path is therefore **HIGH**; original function names remain unknown.

## New authoring/runtime bridge

Instead of forcing the dead-end writer route, v107 correlates the structurally recovered v97 `PUZZLES.DAT` action population against v106 WORLD section 6.

The v97 population contains **40 structurally valid opcode `0x28` action records** representing **13 unique sound stems**. WORLD section 6 contains **400 fixed 27-byte blobs**; exactly **44** of those blobs begin with:

`0x28 + printable NUL-terminated token`

All **17 unique tokens** from those 44 WORLD records resolve independently to WAV files shipped in the demo.

Multiset comparison gives:

- PUZZLES opcode-`0x28` records: **40**
- WORLD section-6 27-byte sound records: **44**
- matched multiset records: **38 / 40 = 95%**
- PUZZLES unique sound stems represented in WORLD: **13 / 13 = 100%**
- PUZZLES-only count after multiset subtraction: **2 × `995`**
- WORLD-only count after multiset subtraction: **2 × `s152v2`, 1 × `996`, 1 × `s121`, 1 × `s188`, 1 × `sr27keys`**

The exact byte-level correspondence is **VERIFIED**. Interpreting it as an authoring/runtime compilation edge is **HIGH**: it is now direct structural evidence that sound-action identity crosses from the PUZZLES representation into WORLD section 6, while other operands are transformed or sourced elsewhere.

## Adversarial control

The same exact `opcode + token + NUL` test was applied to established non-sound demo families:

- `0x17` object/control family: 0 exact matches
- `0x18` moving-object family: 0 exact matches
- `0x19` object pose/target-state family: 0 exact matches
- `0x22` movie family: 0 exact matches

So the result is not a generic consequence of every PUZZLES token simply being copied into WORLD. The sound-action family is special: its sound identity is preserved verbatim at the start of a fixed 27-byte WORLD record while other action families are encoded differently or elsewhere.

## Evidence boundary

v107 does **not** claim that the complete `PUZZLES.DAT -> WORLD.DAT` compiler has been recovered. It establishes a systematic bridge for opcode `0x28` and simultaneously shows that the v106 WORLD-writer caller route is not statically available in the audited reference classes.

Status:

- WORLD reader live runtime path: **VERIFIED/HIGH**
- paired WORLD writer implementation: **VERIFIED**
- paired WORLD writer static caller/fixup reachability: **none found; VERIFIED for audited classes**
- PUZZLES `0x28` ↔ WORLD section-6 sound identity: **HIGH**, with exact binary correspondence **VERIFIED**
- full PUZZLES/ROOMS authoring compiler: **HOLD**

## Next experiment

Reverse the 27-byte WORLD sound-action record and the section-6 reader chain (`0x29E98 -> 0x29CF4 -> 0x29638`). The goal is to identify which numeric/runtime fields replace the second PUZZLES operand/state token. Once that field mapping is recovered, we can test direct action-by-action compilation rather than token-level correspondence.

Reproduce with:

```bash
python tools/analyze_world_puzzle_sound_bridge_v107.py \
  --exe /path/to/R.EXE \
  --world /path/to/WORLD.DAT \
  --puzzles /path/to/PUZZLES.DAT \
  --puzzles-v97 data/puzzles_structural_payload_families_v97.json \
  --canonical-xrefs data/audio/canonical_object_relative_xrefs_v36.json \
  --demo-dir /path/to/ATDEMO \
  --out data/world_puzzle_sound_bridge_v107.json
```
