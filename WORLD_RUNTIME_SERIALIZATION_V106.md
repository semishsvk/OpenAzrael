# OpenAzrael v106 — WORLD.DAT runtime serialization closure

## Result

v103-v105 exhausted the obvious direct runtime-open routes without finding a `PUZZLES.DAT` reader. v106 therefore tests the competing hypothesis from the runtime side: what *is* the game loading as its structured world state?

For the bound demo `R.EXE`, object1 `0x36638` is a direct `WORLD.DAT` loader. It opens `world.dat` in binary read mode, reads a 30-byte header, then deserializes seven top-level count-bearing sections through explicit parser functions and closes the stream.

The reconstructed loader grammar consumes the bound `WORLD.DAT` **exactly to EOF: 96,425 / 96,425 bytes**.

Top-level section counts are:

`[1303, 12, 37, 3, 101, 8, 15]`

This is not a heuristic parse: the section order, count reads, runtime allocation sizes and parser call edges come directly from the loader code.

## Runtime-open chain

- loader: object1 `0x36638`
- mode: `rb`
- filename: `world.dat`
- `fopen` call: `0x36649 -> 0x26004`
- first read: `0x3665E -> 0x260D7`, exactly 30 bytes
- close: `0x3662D -> 0x262A1`

`WORLD.DAT` begins with the embedded build-time header:

`Tue Feb  6 17:27:37 1996\n\0`

The date itself is data from the file; its precise build-system meaning is not inferred beyond that.

## Serialization evidence

The loader creates runtime records and invokes dedicated stream readers. Several of those readers have matching writer functions in the executable:

- `0x28FCC` / `0x28F20`
- `0x35C50` / `0x35CA0`
- `0x27E2C` / `0x27DFA`
- `0x35D88` / `0x35DC4`
- `0x29E98` / `0x29E40`

The shared dynamic-u16-list pair is `0x36058` (reader) / `0x36004` (writer).

The first runtime family allocates 0x5D-byte in-memory records. Its serialized form contains a variable u16 list plus fixed fields and two fixed-size text buffers; the loader contains runtime-only fields that are initialized rather than read from disk. The final family contains nested variable-count structures and ultimately 37-byte and 27-byte serialized blobs. The recovered grammar still reaches EOF exactly.

Therefore:

- `WORLD.DAT` is directly runtime-loaded: **VERIFIED**.
- `WORLD.DAT` is a structured serialization/runtime object database: **HIGH**.

## PUZZLES.DAT adversarial check

The 224 unbiased structural PUZZLES records from v97 contain 133 unique 32-byte action blocks. v106 searched all 133 exact blocks in `WORLD.DAT`:

- exact matches: **0 / 133**

So a simple `PUZZLES.DAT` action-block concatenation/copy into `WORLD.DAT` is excluded for the bound demo.

This does **not** prove that `PUZZLES.DAT` is unrelated to `WORLD.DAT`. If an authoring/export step exists, it can transform the source representation into different runtime structures.

## Evidence boundary

The tempting conclusion “PUZZLES.DAT and ROOMS.DAT are authoring files compiled into WORLD.DAT” is **not yet proven**. v106 raises that route to a concrete, testable hypothesis, but the exact producer edge remains **PROBABLE/HOLD**.

The next experiment should follow the **WORLD writer/caller side** and ask where the in-memory object families supplied to the writer originate. A matching lineage into PUZZLES/ROOMS semantics would close the missing authoring/export edge without relying on filename guesses.
