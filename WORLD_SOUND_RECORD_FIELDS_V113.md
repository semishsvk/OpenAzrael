# OpenAzrael v113 — WORLD opcode-0x28 sound-record field closure

## Result

v20 identified opcode `0x28` as positional sample playback and v107 established a 38/40 multiset bridge between structurally recovered PUZZLES sound actions and WORLD section-6 27-byte records. v113 closes the missing field-level link.

For the bound demo executable/data set, the WORLD section-6 opcode-`0x28` record is 27 bytes and the runtime-consumed fields are now:

| Offset | Size | Meaning | Status |
|---|---:|---|---|
| `+0` | 1 | opcode `0x28` | VERIFIED |
| `+1` | variable C-string area | sound stem; formatted as `%s.WAV` | VERIFIED |
| `+13` | u16 LE | WORLD section-0 object index | VERIFIED |
| `+15` | u16 LE | demo room/context id: 0=R1, 1=R7, 2=R8 | VERIFIED for demo corpus |
| `+17..+26` | 10 | not consumed by the opcode-0x28 handler path | UNKNOWN/HOLD |

This is not inferred only from data correlation. The identities at `+13` and `+15` are closed on the runtime consumer side.

## Runtime chain

The action dispatcher around object1 `0x1870B` reads the opcode byte, accepts opcodes through `0x28`, preserves a pointer to `record+1` in ECX, and dispatches through the action jump table.

The opcode-`0x28` handler begins at object1 `0x191E9`.

It:

1. compares `WORD [record+0x0F]` against the current runtime room/context word reached through global `0x43888`;
2. reads `WORD [record+0x0D]`;
3. uses that value to index the WORLD section-0 pointer array at global `0x43890`;
4. uses the selected section-0 object's name field at runtime offset `+0x34` (11 serialized bytes);
5. resolves the live object/spatial data through the existing scene/object helpers;
6. formats the preserved `record+1` sound stem using `%s.WAV`;
7. invokes `0xD155`, already constrained by v42 as the dynamic 3D sample-start path.

The WORLD loader independently stores the section-0 pointer array into the same `0x43890` global, closing the loader -> serialized index -> runtime consumer chain.

## Ordered PUZZLES -> WORLD correspondence

v107 used a multiset comparison. v113 adds sequence alignment.

- structurally recovered PUZZLES opcode-`0x28` records: **40**
- WORLD section-6 opcode-`0x28` 27-byte records: **44**
- order-preserving LCS matches: **38**
- PUZZLES-only: **2 x `995`**
- WORLD-only, in sequence: `sr27keys`, `996`, 2 x `s152v2`, `s121`, `s188`

Thus the same 38 correspondences survive an order-sensitive test; they are not an artifact of freely pairing duplicate sound stems.

## Section-0 bindings

The 38 aligned records reference 15 section-0 objects. Examples include:

- 1282 -> `doorcor01` (Door)
- 1283 -> `doorcor2` (Door)
- 1277 -> `well_door` (Door)
- 1259 -> `tapestry2` (Tapestry Piece)
- 1255 -> `tapframe2` (Frame)
- 1153 -> `wel_well` (Well)
- 1150 -> `r7p1` (Scroll)
- 1159/1160/1161 -> `zxsound` / `zxsound1` / `zxsound2`
- 1164 -> `font3`
- 140 -> `door`

Room-id validation gives **35/38 direct XAF-manifest matches** and **3/38 independently supported R7 aliases** (`well_door` twice and `r7p1` once), with no conflicting room assignment.

## Evidence boundary

v113 recovers the field-level runtime representation for the sound-action family. It does **not** recover the complete PUZZLES/ROOMS -> WORLD compiler.

The ten trailing bytes `+17..+26` remain explicitly UNKNOWN/HOLD. The opcode-`0x28` handler does not consume them; no semantic label is assigned merely because the bytes exist.

The committed JSON is source-safe metadata only. It contains fingerprints, offsets, names, indexes, mappings and confidence labels; it does not contain raw commercial record bytes.

## Reproduction

The analyzer requires the private/local full evidence corpus:

```bash
python tools/analyze_world_sound_record_fields_v113.py \
  --exe /path/to/R.EXE \
  --world /path/to/WORLD.DAT \
  --puzzles /path/to/PUZZLES.DAT \
  --puzzles-v97 /path/to/puzzles_structural_payload_families_v97.json \
  --manifest-dir /path/to/v44-manifests \
  --demo-rooms-evidence /path/to/demo_rooms_evidence.json \
  --out data/world_sound_record_fields_v113.json

python tools/validate_world_sound_record_fields_v113.py
```

The analyzer checks 20 byte/control-flow/data invariants and fingerprints every non-Git evidence input used for the result.
