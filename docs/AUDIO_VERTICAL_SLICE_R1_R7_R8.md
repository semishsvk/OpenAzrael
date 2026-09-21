# R1 → R7 → R8 Audio Vertical Slice — pre-build validation

## Closed in source
- WORLD v113 verifies opcode 0x28 runtime fields: sound stem, room id and section-0 object index.
- `979tongs` resolves to **R7 / object 1153 / wel_well**.
- Current gameplay code independently proves the tongs/well state chain: rusty tongs are required; successful retrieval acquires `well_key`, sets `R7KeyTake`, and sets `R7key`.
- R8 event graph already binds Lens Place to S137 and Optical Start to S121.

## Deliberate HOLD
These two independent facts do **not** yet prove that the original tongs-use condition dispatches the `979tongs` opcode-0x28 record. The full PUZZLES/ROOMS → WORLD producer/compiler remains HOLD, and the current gameplay event graph does not contain a tongs/well audio action. Therefore automated tests may validate the tongs gameplay state chain, but may not claim original 979tongs playback parity.

## Build gate
The next real Candidate should expose the active room, object/emitter, sound id, requested asset, mode and provenance/confidence in Audio Debug View. Non-capture playback must then demonstrate the event stream. Only that empirical result, or stronger recovered producer/condition evidence, may close the tongs/well audio HOLD.

## Expansion rule
Do not expand to the rest of the demo until the vertical slice has deterministic traversal, state assertions, logical audio assertions for evidence-backed events, and zero false-positive PASS from HOLD bindings.
