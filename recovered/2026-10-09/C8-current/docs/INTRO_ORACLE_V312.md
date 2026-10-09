# Candidate 8 v312: corrected LE mapping and original intro mechanisms

## Acceptance

LE coordinate validation and the source-bound intro implementation pass their
scoped tests. Full Candidate 8 fidelity remains HOLD. This is not a release ZIP.

The native oracle executes the SHA-pinned original R.EXE i386 routines in an
isolated Unicorn fixture. It is NOT a full DOS/VGA runtime capture. Huffman,
keyframe, delta, palette-copy, frame-copy, and PCX decoder instructions execute
from the original executable after ordinary LE relocations. File, allocator,
physical palette, and selected startup OS/display services are explicitly
stubbed at function boundaries. Their identities are recorded in the report.

## Root cause of the old v27/v54/v55 disagreement

The bound executable contains MZ at file 0x352a4. That MZ's e_lfanew is 0x2aa8,
which locates LE at file 0x37d4c. LE table offsets are relative to the LE header,
but its data-page file offset 0x3a400 is relative to the containing MZ module.
Correct data pages start at 0x6f6a4, not 0x7214c.

Old extractors read object bytes 0x2aa8 bytes too late. This caused valid raw
fixups to be compared with the wrong instruction bytes. The independent v312
reader agrees with all 28,547 v27 raw source/target records and all their raw
operand values. The problem was not resolved by applying an arbitrary shift to
fixups: it was resolved by correcting the executable's file coordinate origin.

All eight old operand anchors now land on independently decoded Capstone
disp32 instruction operands. Their old addresses must be tagged
`legacy_shifted_view`; do not silently change historical evidence coordinates.
V54/V55 remain records of failed comparisons in that old view, but their broad
raw-parser/root-cause conclusion is superseded. In particular the +/-32 and
4-KiB searches did not cover the actual non-page-aligned bound-header distance.

`tools/le_bound_image_v312.py` validates MZ/LE discovery, physical page mapping,
object page ownership, raw record boundaries, source lists, signed cross-page
sources, target bounds, and duplicate consistency. Unsupported fixup/page forms
fail closed. Actual ATDEMO has 20 negative page-relative sources and no source
lists; source-list coverage is provided by independent synthetic fixtures,
not falsely claimed from the corpus. The last physical page ends exactly at EOF.

Use this reader for future original-executable RE. Do not reuse the old
LE-header-relative object extraction helpers as instruction-address authority.

## Dispatcher unblocked

Canonical coordinates below are **object 1 relative**, not file offsets:

| Item | Address |
| --- | --- |
| Runtime dispatcher | 0x1b140 |
| Indirect jump | 0x1b1c6 |
| 41-entry dispatch table | 0x1b09c |
| Opcode 0x17 handler | 0x1b51e |
| Opcode 0x18 handler | 0x1b6fc |

All 41 entries are backed by exact raw relocations. This identifies real
handlers; it does not yet verify the complete Well Room pipe interaction.
Do not promote pipe state/animation/audio/persistence fidelity on this alone.

## Original intro mechanisms

All four Huffman groups match the original routine byte-for-byte. All 245
indexed frames and their palettes match the original keyframe/delta routines.
The original image-copy routine is also executed between frames. Delta mode
prefetch can read one extra byte; this is recorded and safely padded in the
fixture, not interpreted as an extra packet byte.

Original startup function object1:0x10799, called at 0x5f3c, executes:

1. MINDLOGO.MOV, caller rate 15, timer period floor(1,000,000 / 15) = 66,666 us.
2. INTRO.MOV, rate 10, timer period 100,000 us; PCM setup passes 22,050 Hz.
3. TITLE.PCX: 631x474 at (0,0) in a 640x480 buffer. The native PCX decoder
   independently matches all 307,200 destination indices, including padding.
4. MOV/INTRO.MOV, rate 10, native 600x300 area centered at (20,90).
5. Return to game startup.

The title caller performs 130 delay calls with argument 20. The Godot title
stage uses the nominal 2.6-second hold. Real DOS delay calibration and fade
curves remain HOLD. The caller also contains three delay calls with argument
30 and palette fade/clear operations; exact temporal reproduction of those
transitions is not claimed by this implementation.

MOV/DEMO.MOV is NOT a startup movie. Its source function 0x10919 is called at
0x607a from the demo-completion route. Godot outro trigger integration remains
open. Skip-flag branches were exercised in the original startup caller; modern
Godot key bindings are not claimed to reproduce original scan-code mapping.

The opaque MOV header word 12 is neither a verified FPS nor a verified depth.
The runtime builder now takes clock, order, and placement from the source
contract, not the old nominal 10-FPS prior-art fallback in decoder metadata.

## Godot changes

The startup player now displays MINDLOGO -> INTRO -> TITLE -> MOV_INTRO while
holding gameplay pause. The legacy title is not flashed a second time afterward.
Scanner/HUD startup follows sequence completion. Skip/abort restores ownership,
input and pause; pre-existing pauses are preserved. Invalid positions/types and
out-of-canvas placement fail closed. A 10-ns numeric comparison tolerance avoids
rejecting valid clock values after Godot JSON round trips; frame periods remain
source-bound integer microseconds.

Movies are positioned in the original 640x480 logical canvas. The poem is not
stretched to fill a widescreen window. Derived PNG/WAV assets remain ignored by
Git and are rebuilt from the read-only corpus. Protected project.godot and
export_presets.cfg have not been edited.

## Reproduction

Use the pinned HomePC Python and Godot documented in the validation receipt.
The native oracle additionally needs Unicorn 2.1.4. Its exact Windows wheel is
cached with SHA-256 in recovery; no shared environment installation is required.

```text
python tools/test_le_bound_image_v312.py
python tools/test_intro_source_contract_v312.py
python tools/validate_original_intro_v312.py ATDEMO --unicorn-path VENDOR --out original.json
python tools/build_intro_assets_v311.py ATDEMO
python tools/validate_intro_fresh_restore_v311.py ATDEMO --godot GODOT --work-root NEW_PATH
```

Set OPENAZRAEL_CORPUS to the pinned ATDEMO directory for corpus tests. Run all
mutating/validation commands under the project's existing foreground writer
guard. The original executable, TITLE.PCX and RESOURCE.CFG are now required restoration inputs
alongside the four MOV files.

## Evidence and remaining gates

`data/evidence/le_mapping_v312.json` contains the eight instruction anchors,
raw record provenance, module origins and complete dispatch bindings.
`data/evidence/intro_native_v312.json` contains native mechanism traces and frame
hashes. `data/evidence/intro_v312_validation.json` summarizes tests and restored
asset fingerprints. `data/tests/intro_source_contract_v312.json` freezes the
extracted startup contract.

New intro tests finish cleanly. Existing controls/Niamh/scanner/HUD runners still
emit their prior ObjectDB shutdown warnings; they are retained in evidence and
not relabelled clean. Full DOS/VGA capture, fade curves, DAC-to-display color,
physical audio timing, original key mappings, macOS runtime, demo outro binding,
Well Room pipe behavior, and full KG-001 release remain separate open gates.
The prior-art license review recorded at v311 still applies before publication.


The movie-directory prefix is not assumed: original constructor 0xb962 reads
three lines of pinned RESOURCE.CFG and assigns its third line (`mov\`) to data
object offset 0x22310 at instruction 0xba89. The native oracle executes this
initializer with explicit file/allocation service fixtures before startup.
