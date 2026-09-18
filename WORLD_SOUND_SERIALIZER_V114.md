# OpenAzrael v114 — WORLD section-6 opaque serializer closure

## Result

v113 recovered the runtime-consumed fields of the 27-byte WORLD section-6 opcode-`0x28` sound-action record. v114 audits the matched reader/writer path to determine whether the remaining bytes are field-aware serialization or an opaque in-memory blob.

The answer is unambiguous for the bound demo executable: the nested WORLD reader and writer serialize both section-6 blob families **wholesale**.

### 27-byte list

Reader chain:

`WORLD reader -> 0x369DC -> 0x29E98 -> 0x29EEA -> 0x29CF4 -> 0x29D2E -> 0x29638`

Inside `0x29638`, the second list:

- reads a u16 count;
- allocates exactly `0x1B` bytes per record;
- reads exactly `0x1B` bytes directly into that allocation;
- appends the pointer to the object's second list.

Writer chain:

`WORLD writer -> 0x3661A -> 0x29E40 -> 0x29E87 -> 0x29D74 -> 0x29DA5 -> 0x2972C`

Inside `0x2972C`, the second list:

- loads each pointer from the list at object offset `+0x08`;
- sets the write size to exactly `0x1B`;
- writes the complete 27-byte allocation with the generic write-like routine `0x30AED`.

The serializer therefore does **not** separately encode the sound stem, section-0 index, room id, or trailing bytes. It persists the complete 27-byte memory record as one fixed blob.

### 37-byte sibling list

The first list follows the same pattern with `0x25` (37) bytes on both read and write. This strengthens the interpretation that these are two fixed-size opaque record families inside the nested section-6 object rather than a special sound-only serializer.

## Immediate-allocation audit

A conservative object-1 scan for the exact pattern `mov eax, 0x1B` followed shortly by a direct call to the established allocator at `0x20C00` finds only one match:

`0x29703 -> 0x29712`

That is the WORLD reader allocation described above.

This excludes a second obvious direct `malloc(27)`-style constructor in the audited pattern class. It does **not** exclude variable-size allocation, alternate allocators, stack/static objects, copy construction, indirect calls, or producer code outside the bound runtime executable.

## Opcode-0x28 residue audit

The bound WORLD contains:

- 400 total 27-byte section-6 records;
- 387 total 37-byte section-6 records;
- 44 opcode-`0x28` sound records.

For the sound records, bytes `+17..+26` are highly non-stable:

- 41 unique 10-byte tails among 44 records;
- 40/44 tails are non-zero;
- only 4/44 are all zero.

More importantly, there are seven duplicated semantic binding groups when records are grouped by:

`(sound stem, section-0 object index, room id)`

All **7/7** groups have different `+17..+26` tails between otherwise equivalent bindings. The strongest example is:

`797tap -> section0[1255] tapframe2 -> R8`

There are 12 such records and **all 12 tails are different**.

The unused remainder of the fixed stem-storage area before offset `+13` also varies in all seven duplicated groups. The serializer preserves those bytes too because it writes the memory block wholesale.

## Meaning of the tail

v114 deliberately does **not** label `+17..+26` as padding, pointers, uninitialized memory, or any other semantic type. The proven facts are narrower:

1. the opcode-`0x28` runtime handler does not consume them;
2. the WORLD serializer does not interpret them;
3. they vary even between records with the same runtime-consumed sound/object/room binding.

Therefore these bytes remain **UNKNOWN/HOLD** and must not be promoted to sound-action gameplay parameters from serialization evidence alone.

## Consequence for the compiler investigation

The section-6 serializer itself is now a dead end for recovering the tail meaning. The next evidence-rich target is construction/mutation of the 27-byte records before serialization: writes into offsets `+17..+26`, copy paths, generic action constructors, or an external authoring/export producer.

This does not change the existing boundary: the complete `PUZZLES/ROOMS -> WORLD` compiler remains HOLD.

## Reproduction

```bash
python tools/analyze_world_sound_serializer_v114.py \
  --exe /path/to/R.EXE \
  --world /path/to/WORLD.DAT \
  --out data/world_sound_serializer_v114.json

python tools/validate_world_sound_serializer_v114.py
```

The analyzer passes 29 machine/data invariants for the bound demo. The committed JSON contains only hashes, offsets, counts and variability summaries; raw commercial record bytes are not committed.
