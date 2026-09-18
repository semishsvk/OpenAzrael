# OpenAzrael v115 — WORLD action-record runtime lifecycle

## Result

v113 recovered the runtime-consumed fields of the WORLD section-6 27-byte opcode-`0x28` sound record. v114 then proved that the matched WORLD reader/writer serializes the 27-byte and 37-byte section-6 records wholesale as opaque fixed-size memory blobs.

v115 follows the 27-byte action record **after deserialization** and closes an important ambiguity: the bound runtime does not create a normalized copy of the action record before opcode execution. The record loaded from WORLD survives by pointer through condition scheduling and is dispatched in place.

## Population path

The nested section-6 object uses two pointer-list insert helpers:

- 27-byte action list insert: `0x295B0`
- 37-byte sibling/condition list insert: `0x295F4`

Across bound executable object 1, their direct rel32 CALL sites are respectively:

- `0x296EC -> 0x295B0`
- `0x2968A -> 0x295F4`

Both callers are inside the WORLD nested reader `0x29638`.

The conservative direct immediate-allocation audit also still finds only one `mov eax,0x1B` followed shortly by a direct call to the established allocator `0x20C00`:

`0x29703 -> 0x29712`

That is the same WORLD reader allocation.

This is **VERIFIED only for the audited direct-call/immediate-allocation classes**. It does not exclude indirect calls, generic/variable-sized allocators, stack/static construction, alternate allocators, copy constructors, or producer code outside the bound runtime executable.

## Shallow pending-action schedule

The condition/scheduling function at `0x2990C`, reached directly from `0x29DDF`, does not copy 27-byte records when a condition becomes active.

Instead it creates a six-byte pending-group entry in the global queue:

- pending group count: global `0x438B0`
- pending group array: global `0x438B4`
- entry size: **6 bytes**

Entry layout:

| Offset | Size | Source | Meaning in audited path |
|---|---:|---|---|
| `+0` | 2 | nested object `+6` | count of 27-byte action pointers |
| `+2` | 4 | nested object `+8` | pointer to the original 27-byte action-pointer array |

The relevant stores are visible around `0x29C47` and `0x29C4E`.

So the pending queue is a **shallow count + pointer-array reference**, not a copied action payload.

## Dispatcher path

The dispatcher at `0x18698`:

1. reads the pending-group count from `0x438B0`;
2. walks entries in an exact six-byte stride;
3. compares the action index with the u16 count at pending entry `+0`;
4. loads the original pointer array from pending entry `+2`;
5. selects `pointer_array[action_index]`;
6. stores that original record pointer locally;
7. reads the opcode byte directly from the original record and dispatches it.

The opcode-`0x28` sound handler at `0x191E9` then reads the v113 fields from that same record. Before its working register is repurposed, the audited handler path performs no store into the record.

## Consequence for the v114 residue

The varying bytes `+17..+26` observed in v114 are therefore:

- already present in serialized `WORLD.DAT`;
- loaded wholesale into the 27-byte allocation;
- retained behind the original pointer;
- shallow-scheduled without copying;
- present unchanged when opcode dispatch begins;
- not consumed by opcode `0x28`.

This eliminates a hidden runtime normalization/copy stage as the source of those bytes in the audited load -> schedule -> dispatch path.

It does **not** identify their authoring origin. Their exact meaning remains **UNKNOWN/HOLD**, upstream of this runtime path.

## Producer boundary

v115 does not recover the complete `PUZZLES/ROOMS -> WORLD` producer/compiler. The next evidence-rich static experiment is outside the established lifecycle path:

- generic copies of exactly 27 bytes;
- record-construction or mutation stores into offsets `+17..+26`;
- action-building helpers using variable/generic allocation;
- indirect/computed reachability into the paired WORLD writer.

Absence in one audited static pattern must not be generalized to proof that no producer exists.

## Reproduction

```bash
python tools/analyze_world_action_lifecycle_v115.py \
  --exe /path/to/R.EXE \
  --out data/world_action_lifecycle_v115.json

python tools/validate_world_action_lifecycle_v115.py
```

The analyzer has 20 bound-executable machine/control-flow invariants. The committed result is source-safe metadata only and contains no raw action-record payload bytes.
