# Candidate 8: source-derived intro movies, v311

Status: **INTRO CODEC AND WINDOWS GODOT PLAYBACK PASS**.
Overall Candidate 8, original-runtime fidelity and the Well Room pipe remain HOLD.
Base checkout: `a7b500fa3ee95c989bf788ccd5a71d6fbbe2be84`.

## Implemented

`tools/decode_intro_mov_v311.py` decodes the four SHA-256-pinned ATDEMO MOV files.
It checks every container boundary, Huffman tree, decoded byte count, frame count,
delta reference, packet type and end of file. No replacement artwork is generated.

| Source | Frames | Distinct images | Audio |
|---|---:|---:|---|
| MINDLOGO.MOV | 40 | 4 | No audio packets |
| INTRO.MOV | 50 | 50 | 121378 unsigned PCM8 mono bytes |
| MOV/INTRO.MOV | 55 | 55 | No audio packets |
| MOV/DEMO.MOV | 100 | 90 | No audio packets |

All 245 decoded frames are represented by 199 lossless PNG files. Palette conversion
uses VGA6 bit replication. The original PCM bytes are preserved in a WAV container.
The Godot importer is explicitly pinned to uncompressed PCM, with normalization,
trimming, resampling and looping disabled. The player rejects a lossy imported stream.

`StartupIntroV311` is the first child of `main.tscn`. Normal startup currently plays
MINDLOGO, INTRO, then returns to the existing title and scanner boot flow. The two
MOV/ subdirectory movies are decoded and playable through `begin([clip_id])`, but
are not automatically bound to an unverified game trigger. Startup ordering and the
10 fps / 22050 Hz policy still require original-runtime comparison; these are not
asserted as final source-runtime fidelity. The value 12 at header offset 6 is opaque.

During playback the game is paused, intro audio remains active, and gameplay input
is consumed. Space, Enter or left click skip the current clip; Escape skips the
sequence. Previous pause/cursor state is restored on completion, skip, missing assets
or removal. Audio mixer completion is awaited so the final audio tail is not cut.
The first processing delta excludes asset-loading time preceding movie start.
The title's 1.5-second candidate fallback timer does not run behind the intro.

Headless regression runs bypass automatic intro startup. Automated gameplay/capture
workflows using a rendered window should explicitly pass `-- --skip-intro` or set
`OPENAZRAEL_SKIP_INTRO=1`. `OPENAZRAEL_FORCE_INTRO=1` enables headless startup testing.
No game save fields, gameplay animations, room bindings or protected project/export
configuration files are changed by the intro player.

## Reproduction on HomePC

Use the existing global writer lease and foreground `lease.py run` guard.
Set `OPENAZRAEL_CORPUS` to the pinned ATDEMO directory for the corpus tests.

```text
python tools/decode_intro_mov_v311.py ATDEMO --out assets/intro_v311
python tools/build_intro_assets_v311.py ATDEMO --reuse-decoded
Godot_v4.7.2-stable_win64.exe --headless --path CHECKOUT --editor --import
python tools/test_intro_mov_v311.py
Godot_v4.7.2-stable_win64.exe --headless --path CHECKOUT res://scripts/validation/intro_runtime_test_v311.tscn
Godot_v4.7.2-stable_win64.exe --path CHECKOUT res://scripts/validation/intro_main_scene_test_v311.tscn
Godot_v4.7.2-stable_win64.exe --path CHECKOUT res://scripts/validation/intro_av_test_v311.tscn
python tools/validate_intro_fresh_restore_v311.py ATDEMO --godot GODOT --work-root NEW_EMPTY_RESTORE_PATH
```

The build helper can perform decoding itself when `--reuse-decoded` is omitted.
It writes `data/runtime_generated/intro_movies_v311.json` for resource export.
The per-clip asset manifests and commercial-derived images/audio remain ignored by
Git. Restore them from the original corpus; do not publish the commercial payload.
Do not use old Candidate ZIPs to assess this change: those ZIPs are not rebuilt here.

## Evidence and acceptance

* Decoder: 27 tests, including all four actual corpus fixtures and malformed inputs.
* Independent Huffman cross-check: all four first groups match the existing RES
  implementation byte-for-byte, including complete word consumption.
* Godot playback harness: 30 checks; every one of the 245 imported frame images
  matches decoded RGB bytes; imported audio matches the original PCM bytes.
* Real main scene / NVIDIA OpenGL capture: 16 checks, five native-size pixel-exact
  viewport captures, widescreen pillarboxing, title/input/pause/save-state/scanner flow.
* Real audio/process clock: nine checks, all 50 IG frames, full audio tail,
  non-silent engine-bus capture and bounded internal audio/video clock skew.
* Two independent source-to-assets-to-Godot restores produce 205 identical files
  and both pass all 30 playback checks. This is an isolated intro harness, NOT the
  full Candidate 8 fresh-checkout gate.
* Controls/sniper v304, scanner v164, HUD startup v215 and Niamh scene v256 are
  rerun separately. Their shutdown warnings are retained in the validation report,
  not silently reclassified as clean logs or fidelity evidence.

See `data/evidence/intro_v311_validation.json` for fingerprints and measured results.
Raw logs, captures and two restore runs are retained in the HomePC recovery checkpoint.
MacOS playback, original executable timing/order/palette comparison, auxiliary movie
trigger binding, Well Room pipe and overall KG-001 release acceptance remain open.
No final Windows/macOS Candidate ZIP is created by this work.

## Binary format corrections to v308-v310

The 30-byte file header is followed by 16-byte group headers (magic 0xEE9901CF).
The first group is static-Huffman compressed; later groups in these four files are raw.
The value at file offset 0x28 is a compressed byte count, not a frame offset.
The apparent table at 0x436 is the internal-node half of the Huffman child table:
its full table starts at 0x36 and contains 1024 little-endian 16-bit children.
The bitstream starts at 0x836 and is consumed least-significant bit first, padded
in 32-bit words. Literal nodes are below 256. Inner records use magic 0x0123FEDC.
Types 1/4/5 are indexed keyframe/delta/palette, and 6/7 are mono/stereo PCM8.
Type-4 deltas use source-derived 4x4 tiles, including skip runs, literal blocks,
short previous-frame motion and wide previous/current-frame motion.
The old `depth_candidate=12` interpretation is explicitly superseded as unproven.

## External prior art and provenance

Kostya's primary reverse-engineering article identifies static Huffman coding:
https://codecs.multimedia.cx/2024/03/a-look-at-compressed-game-video-formats/

NihAV Game Tool is a separate reference, not a fidelity authority or bundled runtime:
https://nihav.org/game_tool.html
https://nihav.org/na_game_tool-0.6.0.tar.bz2
Archive SHA-256: 39a6174a20104c2d2065f37b304253aaf3393aa724b1c153ab374b5711cb3845.
Reference files: `src/input/decoders/azmov.rs`, `src/input/util/mod.rs`, `COPYING.GPL3`.
The archive was inspected; its Rust executable was NOT built or run. Delta semantics
and nominal timing were checked against that reference. No third-party source is
committed. License/reuse review remains required before public source distribution;
this checkpoint is private local implementation/evidence, not a public release.

Godot audio representation/import reference:
https://docs.godotengine.org/en/stable/classes/class_audiostreamwav.html
https://docs.godotengine.org/en/stable/classes/class_resourceimporterwav.html


## Superseded startup policy: v312

The v311 decoder remains valid (245/245 frames now match original R.EXE instructions). Its nominal 10-FPS startup policy and two-movie sequence are superseded by docs/INTRO_ORACLE_V312.md. Normal startup now follows Mindscape (15-FPS caller) -> Intelligent Games -> original TITLE.PCX -> MOV/INTRO poem, then gameplay. Native LE object extraction is corrected in tools/le_bound_image_v312.py.
