# OpenAzrael Godot POC v56

**v56 forensic correction:** a clean-room IBM LE fixup parser independently reproduces 28,547 records, but still yields zero exact matches on the eight known `0xCDE1` disp32 anchors. More importantly, v28's claim that `Data Pages Offset` is absolute in the bound file is superseded: the coherent object image begins at `LE_header + Data_Pages_Offset` (`0x7214C`). Exact attenuation/pan constants remain HOLD; no guessed constants are used. See `CLEANROOM_LE_AUDIT_V56.md`.

## OpenAzrael v30 forensic update

Added x86 operand-boundary validation for LE fixup sources. See `docs/LE_FIXUP_OPERAND_VALIDATION_V30.md` and `data/audio/fixup_operand_validation_v30.json`. Target relocation semantics remain HOLD.

# OpenAzrael Demo Reconstruction — Godot POC v18

v17 is a forensic-correction checkpoint. It cross-checks the demo against the
full retail data and replaces several Baptistery approximations with direct
logical-object -> XAF mappings recovered from retail `OBJECTS.DAT`.

## New in v18

- Retracted the tempting `0x0726 = 1830 ms` interpretation near `RaiseTimer`.
  A corpus scan shows the same `0x16 + u16 + token` pattern throughout the
  compiled puzzle database; all recovered tags are multiples of ten and the R8
  sequence 1820/1830/1840/1850 tracks neighboring source concepts. It is much
  more likely compiler/source metadata than elapsed time.
- Confirmed the exact `16 26 07 RaiseTimer` bytes are shared with retail.
- Found partially overwritten original puzzle-DSL text embedded near the end of
  both demo and retail `PUZZLES.DAT` (`PUZZLE :`, `START STATE`, `DECLARE :
  Flag`, `R8RaiseTimer`, `R8Counter`, etc.). This changes the reverse-engineering
  model from a clean data table to a compiled graph retaining source artefacts.
- Tested both authored hinge directions for `DoorR8`. +90 degrees swings the
  door out of the Shield chamber; -90 swings it into the chamber footprint.
  +90 is therefore retained as the geometry-supported candidate, though the
  original animation opcode is still not recovered.
- Added a reproducible software control render of the R8 closed/open state.

See `docs/R8_TIMER_DOOR_FORENSICS_V18.md`.

## New in v17

- Proved that the late demo override table in `ROOMS.DAT` uses 60-byte entries.
  The demo adds exactly four 60-byte records (`R1Entry`, `TongR6`,
  `R1DemoTapPiece1`, `WellRoomdoor`) and removes one (`R8FromR6`). Net: +180 B,
  exactly matching demo-vs-retail file size.
- Important nuance: this 60-byte stride is proven for that late table only, not
  for the whole `ROOMS.DAT` file.
- Cross-checked demo vs retail `PUZZLES.DAT`: a 512-byte window around
  `R8RaiseTimer` is 100% identical, while the neighboring R8 mechanism blocks
  are ~96–98% identical. The core Baptistery mechanism is production logic.
- Recovered direct retail object mappings that line up with demo XAF objects:
  - `R8LensPlace` -> `lenstop`
  - `R8LensLook` -> `lenstop01`
  - `R8LensZone` -> `zxplate`
  - `DoorR8` -> `door`
  - `R8TapestryBack` -> `tapestry2a`
- Corrected the secret-door implementation: `DoorR8` now animates the authored
  vertical `door` mesh around its hinge-like XAF pivot. `secretflor` is no longer
  moved; geometry shows it is the Shield chamber floor.
- The optical activation check now uses the exact authored transparent
  `zxplate` footprint instead of a hand-tuned radius around the visible plate.
- `lenstop` and `lenstop01` are the same lens mesh at two authored poses. v17
  uses those exact poses as the optical-stage endpoints.
- Runtime state taxonomy is cleaner: persistent/source flags and transient
  puzzle/event nodes now have separate dictionaries in `DemoState`.

## Still reconstructed / not yet exact

- The interpolation time for `lenstop -> lenstop01` still uses the original
  `S121.WAV` duration as a proxy until the exact timer opcode is decoded.
- `DoorR8` opens +90 degrees over the original `799SECDR.WAV` duration. The
  authored hinge is real; the exact direction and angular curve remain to be
  verified from runtime code/data.
- Godot is not installed in this analysis environment, so the project is
  statically/data validated but not runtime-launched here.

## Controls

WASD move, Shift sprint, mouse look, E interact. Keys 1/2/3 remain debug
teleports to R1/R7/R8.

See `docs/DEMO_RETAIL_FORENSICS_V17.md` for the byte-level evidence.

## v19 — compiled puzzle action archaeology + Watcom LE unbinding

v19 shifts the R8 sequence from hand-labelled state names toward a recoverable action IR.
A recurring `PUZZLES.DAT` action shape (`10 00 <opcode> <token>`) was compared across the demo and full retail puzzle corpora, `FLAGLIST.DAT`, `OBJECTS.DAT`, and diagnostics embedded in `R.EXE`.

High-confidence operation families now include:

- `00`: add/start named timer — `R8RaiseTimer` is an action of this family.
- `04`: operation on a persistent flag (exact set/clear/toggle mode still pending).
- `07`: add object to room.
- `08`: remove object from room.
- `09`: remove inventory item.
- `1F`: room transition/teleport family.
- `22`: play movie.
- `28`: play sound/sample.

This is important for Baptistery: `R8RaiseTimer` is now positively identified as a *timer action name*, not a hidden millisecond number. We still need the timer interval/threshold stored elsewhere in the graph.

The original `R.EXE` has also been cleanly located as a DOS/4GW-bound 32-bit Watcom LE image. The valid LE header begins at bound-file offset `0x37D4C`; the module has two objects, 305 pages, 4 KiB pages, and AUTODS object 2. The current LE parser structurally walks 28,547 fixup records without crossing a fixup-page boundary. Original executable bytes are deliberately excluded from this checkpoint; only reverse-engineering tools and metadata are included.

See:

- `data/puzzle_action_opcode_evidence_v19.json`
- `data/puzzle_action_opcode_retail_corpus_v19.json`
- `data/puzzle_opcode_semantics_v19.json`
- `data/r8_compiled_action_slice_v19.json`
- `data/r_exe_le_layout_v19.json`
- `docs/PUZZLE_ACTION_OPCODE_NOTES_V19.md`
- `docs/R_EXE_LE_RE_NOTES_V19.md`

## v20 reverse-engineering update

The Watcom LE jump-table fixups have now been resolved into concrete ProcessResponses case addresses. Opcode 0x00 and 0x01 are confirmed directly from executable code as timer start/stop operations. The timer runtime structure is substantially recovered, and the serialized R8RaiseTimer definition supports a one-shot threshold of 4 **engine timer ticks** (tick-to-seconds cadence remains unresolved). Opcode 0x18 is confirmed to consume authored movement operands, so DoorR8's exact motion should be recoverable from PUZZLES.DAT rather than approximated.

## v21 — original spatial-audio/world IR in exporter

- Added `export_legacy_world_v21.py` to turn original AMB/NPC/audio data into engine-neutral OpenAzrael IR.
- Full demo audio census is now exported: 30 WAV, 24 XMI, 3 AMB maps, 7 verified ambient XYZ emitters.
- NPC*.DAT position/direction prefixes are exported as additional original world-coordinate evidence (12 demo state instances).
- Added XAF exporter v8. It optionally attaches the matching original room audio evidence to its manifest via `--legacy-ir` and `--room-id`.
- Source coordinates are deliberately preserved and the Godot transform remains `PENDING_CALIBRATION`; canonical export does not bake in an unverified scale/handedness/offset.
- Original audio assets are retained under `data/audio/original_audio`; runtime Classic/Enhanced rendering remains a later layer.

See `docs/AUDIO_LEGACY_EXPORT_V21.md`.


## v22 audio checkpoint
Original AMB0/1/2 spatial emitters now spawn in Godot from legacy_world_ir.json using the demo-calibrated identity XYZ transform. See docs/COORDINATE_AUDIO_RUNTIME_V22.md.


## v23 audio checkpoint
Evidence-aware Classic/Enhanced ambient renderer; R.EXE Miles AIL volume/pan backend evidence captured. See `docs/R_EXE_3D_AUDIO_FORENSICS_V23.md`.


## v24 audio-forensics update
`tools/analyze_play3d_v24.py` makes the Play3DSample/Miles evidence reproducible in `data/audio/play3d_forensics_v24.json`. Runtime Classic mode is `CLASSIC_FORENSIC_V24`; original samples/XYZ are evidence, while attenuation/pan remain HOLD pending LE xref recovery.

## v26 forensic checkpoint
`tools/resolve_le_fixups_v25.py` now resolves Watcom LE source/target fixup coordinates. See `docs/LE_FIXUP_RESOLVER_V25.md`. Exact fixup xrefs to the Play3D diagnostic labels remain absent, so Classic attenuation/pan stays HOLD pending named-import call-site recovery.


## v26 forensic checkpoint
Added `tools/audit_miles_xrefs_v26.py` and `data/audio/miles_xref_audit_v26.json`. This checkpoint deliberately does not change Classic attenuation: nearby relocations around Miles diagnostic strings are not sufficient call-site evidence. See `docs/MILES_CALLSITE_FORENSICS_V26.md`.


## v27 forensic gate
Added `tools/validate_le_fixup_semantics_v27.py` and `data/audio/le_fixup_semantics_audit_v27.json`. LE fixup source→target semantics are now explicitly HOLD until a relocation invariant is independently validated; audio runtime evidence is unchanged.

## v28 forensic update
LE physical page mapping was corrected: the demo executable's Data Pages Offset is treated as an absolute file offset. All 27,683 type-7/internal fixup source locations are now readable. The v27 pre-relocation raw-dword equality test is retired as an invalid invariant. See `docs/LE_PAGE_MAPPING_V28.md`.

## v31 forensic update
Added `tools/audit_fixup_records_v31.py`, `data/audio/fixup_raw_record_audit_v31.json`, and `docs/LE_FIXUP_RAW_RECORDS_V31.md`. v31 preserves raw LE fixup records byte-for-byte and correlates them with operand-aligned x86 candidates. Record/source parsing is promoted independently; loader relocation semantics remain HOLD.

## v33 forensic milestone
LE type-7 fixups are now represented as selector/object-relative `OFFSET32` references. The canonical xref key is `(object, offset)`; preferred linear addresses are diagnostic only. See `docs/LE_OBJECT_RELATIVE_XREFS_V33.md` and `data/audio/trusted_object_relative_xrefs_v33.json`.

## v34 forensic correction
v34 audits the LE fixup interpretation against the published LE/LX format and Open Watcom definitions. The v33 object-relative xref graph remains useful, but the claim that source type `07h` implies `runtime_patch_value = target_offset` has been withdrawn. See `docs/LE_FIXUP_SEMANTICS_CORRECTION_V34.md` and `data/audio/le_fixup_semantics_correction_v34.json`.

## v35 forensic checkpoint
Validated signed LE `SRCOFF` semantics against the demo corpus: 20 cross-page OFFSET32 continuation records were found, exclusively at -1/-2/-3 (7/7/6), exactly as expected for a four-byte relocation. See `docs/LE_CROSS_PAGE_FIXUPS_V35.md`.


## v36 forensic update
Canonical LE xref graph now contains **28,527** logical object-relative references after collapsing exactly **20** cross-page duplicate records. The demo raw flags contain no source-list or internal-chain records, so no speculative chain expansion is performed. See `LE_CANONICAL_XREFS_V36.md`.

## v37 forensic audio update

v37 identifies a HIGH-confidence x86 3D-audio update-core candidate at object-1 `0xCDE1..0xD134`. It contains XYZ subtraction, a distance-like helper, a gain path clamped to 99, and two per-sample setter wrappers that are PROBABLE pan/volume paths. See `docs/AUDIO_3D_CORE_RECOVERY_V37.md`. Exact constants and the final `Play3DSample` name binding remain HOLD.

## v38 forensic checkpoint

v38 independently identifies the v37 distance-derived setter path as Miles sample **volume** and the directional setter path as sample **pan** (HIGH confidence). See `docs/MILES_SETTER_IDENTITY_V38.md`. Exact numeric attenuation/pan formula remains HOLD pending runtime constant recovery.

## v40 forensic checkpoint
v40 validates the caller topology of the original 3D audio core at object-1 `0xCDE1`: four exact direct callers, a six-dword/two-XYZ ABI, three sample-start paths, and one continuous update path. Exact numeric attenuation/pan constants remain HOLD pending runtime/initializer recovery. See `docs/AUDIO_3D_CALLERS_V40.md`.

## v41 forensic checkpoint
v41 refines the original 3D audio ABI: `0xCDE1` receives listener position XYZ plus listener orientation/forward XYZ. The seven source positions are stored separately in the 24-byte emitter table at `0x227E8`. See `docs/LISTENER_3D_ABI_V41.md` and `data/audio/listener_3d_abi_v41.json`.

## v42 forensic + runtime checkpoint
v42 closes the room-ambient loader path at HIGH confidence: object-1 `0xD7BF` loads at most three room ambient records into reserved 3D slots 0..2 via `0xD523`; dynamic 3D samples use slots 3..6, for seven 24-byte runtime records total. `legacy_ambient_audio.gd` now mirrors the verified ambient slot capacity and provenance. See `docs/AMBIENT_LOADER_PIPELINE_V42.md` and `data/audio/ambient_loader_pipeline_v42.json`.

## v43 forensic checkpoint
v43 closes the AMB filename-to-runtime-handle path at instruction level: the filename buffer parsed by `0xD7BF` is passed in EBX to `0xD523`, recovered into EDX, passed through `0x1EF44` to resource/sample resolution `0x1FE7F`, and the returned sample index/handle is stored at `emitter[slot]+0x0C`. See `docs/SAMPLE_FILENAME_TO_HANDLE_V43.md` and `data/audio/sample_filename_to_handle_v43.json`.

## v44 Classic graphics checkpoint
The playable demo now ships re-exported **textured** R1/R7/R8 GLBs plus all 86 decoded demo AZF textures under `assets/textures/classic`. Run `python tools/validate_graphics_pipeline_v44.py` to verify geometry, UV and embedded-texture invariants. See `docs/GRAPHICS_PIPELINE_V44.md` for confidence boundaries.

## v45 audio checkpoint
v45 reconstructs the original sample resource/cache and Miles sample lifecycle below the AMB filename→handle path. See `AUDIO_SAMPLE_LIFECYCLE_V45.md` and `data/audio/sample_lifecycle_v45.json`. Exact unresolved numeric constants remain HOLD.

## v45 audio checkpoint
v45 reconstructs the original sample resource/cache and Miles sample lifecycle below the AMB filename→handle path. See `AUDIO_SAMPLE_LIFECYCLE_V45.md` and `data/audio/sample_lifecycle_v45.json`. Exact unresolved numeric constants remain HOLD.

## v46 Classic Audio checkpoint
v46 traces the demo AMB call-site constants through the sample-start path. The original room-ambient path passes numeric loop-count **0** to `AIL_set_sample_loop_count` immediately before start, and the sample runtime defaults feeding the confirmed Miles setters are **pan 64 / volume 64** (HIGH). Infinite-loop interpretation is retained as PROBABLE; `0x3974F`, the literal `1000`, and exact 3D attenuation/pan mathematics remain HOLD. See `docs/AMBIENT_PLAYBACK_DEFAULTS_V46.md`.

## v47 audio checkpoint
v47 binds `0x3974F` to `AIL_set_sample_playback_rate` (HIGH) and its paired getter `0x397C5` to `AIL_sample_playback_rate` (HIGH). It also separates the rate field from a different sample-pool field seeded with literal 22050. The initialization path passes numeric rate 0; the semantics of 0 and the role of the separate 22050 field remain HOLD rather than guessed.

### v48 forensic correction — playback rate vs sample position
v48 supersedes the v47 wrapper identity. A stronger dedicated setter dataflow shows that whole-record `+0x10` is the playback-rate field and is initialized to **22050**; engine routine `0x1F4A5` writes it and calls wrapper `0x38D8C` (HIGH). Whole-record `+0x08`, initialized to **0**, instead routes through `0x3974F` with paired getter `0x397C5` and is the sample-position field (HIGH). Current defaults are therefore position 0 / pan 64 / playback rate 22050 / volume 64. See `docs/SAMPLE_RATE_POSITION_CORRECTION_V48.md`.

## v49 — Classic Audio playback-rate call-site closure

v49 traces all direct demo `R.EXE` callers of the verified playback-rate setter `0x1F4A5`. Exactly three direct call sites exist (`0x5009`, `0xE552`, `0xE590`) and all explicitly select 22050. Classic demo playback rate is therefore HIGH at 22050 for the observed direct-call graph. The AMB literal 1000 remains HOLD pending clean packed-ABI resolution. See `docs/PLAYBACK_RATE_CALLSITES_V49.md` and `data/audio/playback_rate_callsites_v49.json`.

### v50 forensic correction — ambient loop ABI
v50 re-audits the packed register/stack ABI and corrects v46: the room-ambient value reaching `AIL_set_sample_loop_count` is **1000 (HIGH)**, not 0. The separate zero is a control flag consumed by branching in `0x1EDD7`. The restart path independently uses the same `1000,0` pair. v46 is retained as history but is explicitly superseded; the exact Miles semantic interpretation of numeric 1000 remains HOLD. See `docs/AMBIENT_LOOP_ABI_CORRECTION_V50.md`.

### v50 forensic correction — ambient loop ABI
v50 re-audits the packed register/stack ABI and corrects v46: the room-ambient value reaching `AIL_set_sample_loop_count` is **1000 (HIGH)**, not 0. The separate zero is a control flag consumed by branching in `0x1EDD7`. The restart path independently uses the same `1000,0` pair. v46 is retained as history but explicitly superseded; the exact Miles semantic interpretation of numeric 1000 remains HOLD. See `docs/AMBIENT_LOOP_ABI_CORRECTION_V50.md`.

## v51 Classic 3D math checkpoint

v51 originally proposed canonical LE reference identities for the remaining attenuation/pan data. **Superseded by v52:** operand-alignment and object-2 byte checks invalidate those specific semantic bindings. Numeric values remain HOLD and no v51 target is used by Classic Audio.

## v52 xref-alignment correction

v52 adversarially rechecks the v51 3D constant bindings against coherent x86 instruction boundaries and reconstructed object-2 bytes. It **withdraws/supersedes** the v51 `object2:0x6ABC/0x6ABE/0x1724` semantic bindings: the v36 source coordinates used by v51 do not land on the actual disp32 operand starts, and object2:0x1724 lies inside `AIL_set_sample_volume` diagnostic text. Classic attenuation/pan numeric constants remain HOLD; no guessed value is promoted into runtime code. See `docs/AUDIO_3D_XREF_ALIGNMENT_V52.md`.

## v53 forensic safety checkpoint
v53 quarantines operand-level semantic use of `canonical_object_relative_xrefs_v36.json`. The corpus remains useful structurally, but it must not bind 3D-core operands to runtime constants/APIs until LE source/target semantics are independently revalidated. `data/audio/fixup_graph_quarantine_v53.json` also records eight exact raw x86 `disp32` anchors for the Classic 3D attenuation/pan path. This supersedes the unsafe v51 target-binding approach and preserves the v52 correction as a project-wide invariant.

## v54 forensic correction

v54 strengthens the LE-relocation quarantine: eight independently decoded absolute `disp32` operands in the original 3D core have zero exact matches in the legacy v27 source-coordinate mapping, while that mapping emits many nearby type-7 records. Operand-level source mapping from v27/v30/v33/v36 is therefore superseded/HOLD. Classic Audio keeps only instruction-level facts until a replacement LE mapper passes all eight anchors. See `FIXUP_SOURCE_MAPPING_V54.md` and `data/audio/fixup_source_mapping_audit_v54.json`.

## v55 forensic checkpoint
v55 adversarially tested whether the quarantined LE fixup source coordinates could be repaired with a simple constant, instruction-prefix, object-base, or 4 KiB page shift. They cannot. `data/audio/fixup_remap_hypotheses_v55.json` rejects heuristic offset patching; exact attenuation/pan constants remain HOLD until a clean raw-record reparse matches all eight known 3D-core operand anchors.

## v57 forensic checkpoint
v57 audits the initialized LE data independently of the quarantined legacy xref graph. It proves that the raw `0xCDE1` disp32 values are relocation placeholders rather than literal attenuation/pan constants, confirms object 2 base/layout, and shows that the suspected `0x6abc/0x6abe` area is zero-initialized while `0x1724` is diagnostic text. Exact Classic 3D numeric constants therefore remain HOLD pending relocated-image/runtime-initialization reconstruction. See `INITIALIZED_DATA_AUDIT_V57.md`.

## v58 forensic audio update
v58 independently recovered the nine-qword numeric constant lattice used by the original `0xCDE1` 3D-audio math: `180, 3.141592, 360, -180, 90, -90, 63, 64, 15000`. This does not rely on the quarantined v27-v36 operand-level xref mapping. The strongest new result is `K_DISTANCE = 15000` (HIGH), with the angle/pan constants also HIGH. The global-volume runtime word remains HOLD. See `AUDIO_3D_CONSTANT_LATTICE_V58.md` and `data/audio/audio_3d_constant_lattice_v58.json`.

## v59 — executable Classic 3D reference math

v59 adds `tools/build_classic_3d_reference_v59.py` and golden vectors for the HIGH-confidence angle-domain pan branch and distance-domain attenuation branch. It deliberately keeps XYZ→heading helper semantics and runtime global-volume state on HOLD rather than overclaiming full spatial parity.

## v61 — Classic XYZ heading closure
v61 identifies the math helpers behind the remaining heading path: `0x36D86` executes the normal x87 square-root path and `0x472D9` is `FXCH; FPATAN; RET`. Together with the caller dataflow this closes the normal non-zero X/Z -> heading path as HIGH. `scripts/classic_3d_reference_v61.gd` is a deliberately non-active reference implementation; live playback remains unchanged pending coordinate/parity validation. See `CLASSIC_XYZ_HEADING_V61.md` and `data/audio/heading_helpers_v61.json`.


## v62 forensic correction
The v61 closed-form XYZ heading interpretation is superseded after an adversarial cardinal-direction test exposed a 0°/360° collision for opposite X directions. Instruction-level facts remain retained; exact `0x30D7A` semantics and full XYZ-to-pan are HOLD. `scripts/classic_3d_reference_v62.gd` exposes only the safe attenuation and heading-independent pan stages. See `docs/HEADING_SEMANTICS_CORRECTION_V62.md`.

## v63 — x87 heading constant resolved
v63 independently decodes the adjacent 80-bit x87 literal used by the `0x30D7A` normal path as π/2 and closes the helper itself as an asin-equivalent construction. This does **not** restore the superseded v61 complete XYZ-heading interpretation: caller-level endpoint/quadrant semantics and full XYZ→pan remain HOLD. See `docs/HEADING_CONSTANT_V63.md` and `data/audio/heading_constant_resolution_v63.json`.

### v64 full-pipeline adversarial correction
v64 propagates the v61/v63 XYZ-heading interpretation through the complete retained pan branch without modulo-normalizing 0°/360°. Antipodal X directions still collapse to the same pan/mode output, so the v61/v63 complete semantic interpretation remains superseded. The π/2 literal and instruction-level FSQRT/FPATAN facts are retained; complete XYZ→heading/pan remains HOLD. The v58 ordered placeholder→literal correspondence is now PROVISIONAL for angle constants pending independent binding. See `docs/FULL_HEADING_PIPELINE_AUDIT_V64.md`.

## v65 — x87 heading helper corrected to acos
v65 resolves the v64 cardinal collision by tracing the x87 stack through both reverse-subtract operations. `0x30D7A` normal-domain semantics are `acos(z)`, not the previously assumed asin-equivalent final result: FPATAN produces the asin intermediate, then the verified π/2 literal and final reverse subtraction form `π/2 - asin(z)`. Eight compass-direction tests are distinct and antipodal directions no longer collide. The v58 caller angle-constant relocation binding remains PROVISIONAL, so the new Godot reference stays non-active. See `docs/HEADING_ACOS_CLOSURE_V65.md`.

## v66 — authentic AMB parity fixtures
v66 adds a deterministic legacy-coordinate parity harness over all seven VERIFIED ambient emitters from `AMB0.SND`/`AMB1.SND`/`AMB2.SND`. It generates 28 synthetic-listener regression cases with distance, heading, pan, rear divisor, gain, and volume outputs while explicitly keeping the Azrael→Godot transform and v58 caller-angle relocation binding gated. See `docs/CLASSIC_AMBIENT_PARITY_V66.md` and `data/audio/classic_ambient_parity_v66.json`.

## v67 — demo coordinate transform closure
v67 cross-validates the existing identity transform against all seven VERIFIED AMB emitters and all 12 explicit NPC state instances. The demo transform is now HIGH: `Vector3(x,y,z)`, scale 1, no axis/sign/origin correction. Per-room IR and NPC instances are updated from stale `PENDING_CALIBRATION` to `CALIBRATED_DEMO_V67`; original legacy coordinates remain preserved. Retail/full-game global identity remains HOLD pending cross-validation. See `docs/DEMO_COORDINATE_CLOSURE_V67.md` and `data/audio/demo_coordinate_closure_v67.json`.

### v68 — Classic 3D runtime shadow parity backend
v68 wires the reconstructed Classic 3D math into a **shadow/debug backend** beside the existing Godot `AudioStreamPlayer3D` renderer. Every active authentic AMB emitter can now expose live reconstructed distance, listener/source heading, folded angle, Miles pan, rear divisor and volume without changing playback. The backend uses the v67 demo identity coordinate transform and remains non-authoritative while caller angle-constant binding is PROVISIONAL. `validate_classic_parity_runtime_v68.py` must reproduce all 28 v66 golden fixtures before live Classic playback is allowed.

## v69 — live Audio Debug View
Press F8 in the demo to display the Classic 3D shadow backend for each authentic room AMB emitter: original XYZ, distance, listener/source headings, folded angle, Miles pan, rear divisor, and reconstructed volume. The overlay is observational only; provisional forensic values still do not drive playback. See `AUDIO_DEBUG_VIEW_V69.md`.

## v70 — Classic 3D constant semantic audit

Adds `tools/audit_angle_constant_semantics_v70.py` and `data/audio/angle_constant_semantic_audit_v70.json`. The nine-double Classic 3D literal sequence is unique in object 1 and caller algebra is independently revalidated. Semantic values are HIGH; LE relocation binding remains PROVISIONAL, so Classic playback remains shadow-only.

## v71 — independent runtime audio parity capture
- F9 appends an evidence-separated JSONL snapshot to `user://openazrael_audio_capture_v71.jsonl`.
- Captures listener pose, active authentic AMB emitters and the reconstructed Classic pan/volume reference.
- Original-demo observations remain explicitly `UNOBSERVED` until independently populated.
- `tools/compare_runtime_parity_capture_v71.py` performs exact pan/volume comparison and refuses to treat unobserved records as parity evidence.
- Live Classic playback remains unchanged/shadow-only.

## v72 — original-runtime Miles observation bridge
v72 discovers that the bound demo R.EXE already includes Miles AIL diagnostic tracing for `AIL_set_sample_pan` and `AIL_set_sample_volume`, providing a safer no-binary-patch path to independent parity observations. It adds a static audit plus a conservative trace importer that refuses to guess Miles-handle→legacy-slot identity. See `AUDIO_ORIGINAL_RUNTIME_BRIDGE_V72.md`.

## v73 — Miles lifecycle capture protocol
v73 expands the no-patch original-runtime bridge to the verified Miles lifecycle diagnostic vocabulary and adds a conservative per-handle trace parser. It does not guess handle-to-AMB-slot identity.

### v74 — Miles handle bridge
v74 corrects the remaining engine-index/Miles-handle ambiguity. The 3D emitter `+0x0C` field is a signed engine sample-pool index. Pan/volume wrappers resolve it through the 36-byte audio sample pool and load the actual Miles sample handle from `pool[index]+0x04` before calling AIL. This closes the static AMB → engine index → Miles handle dataflow at HIGH confidence while deliberately leaving concrete runtime handle values and automatic trace-to-AMB mapping on HOLD. See `AUDIO_MILES_HANDLE_BRIDGE_V74.md` and `data/audio/miles_handle_bridge_v74.json`.

## v75 — original sample-pool allocator closed
v75 proves the automatic sample-slot policy in `0x1EDD7`: requested index `-1` scans pool indices upward from 0, queries `AIL_sample_status` on `pool[index]+0x04`, treats status bit `0x04` as busy, and selects the first non-busy slot. Concrete AMB->pool indices remain runtime-dependent and are not inferred from trace chronology.

### v76 — runtime audio snapshot closure
v76 closes the minimal original-runtime snapshot structure without patching `R.EXE`: the audio manager allocation is 0x364 bytes, its initialized Miles sample pool contains 8 records of 36 bytes, and each record stores the Miles handle at +0x04. Combined with the seven 24-byte 3D emitter records and their +0x0C pool indices, a manager dump + emitter dump can now recover exact runtime emitter → pool index → Miles handle joins. Static operands `0x41D9C` and `0x227E8` are deliberately not treated as final DOS linear addresses while LE relocation mapping remains quarantined. See `AUDIO_RUNTIME_SNAPSHOT_V76.md`.

## v77 — same-object runtime address resolver
v77 closes the remaining static-to-runtime address *method* for the original audio snapshot without guessing a DOS load base or reviving the quarantined LE fixup graph. The spatial core, listener cache, emitter table, and audio-manager global are all verified offsets inside reconstructed LE object 1. One debugger-observed runtime address of the `0xCDE1` spatial-core signature is sufficient to derive the other audio addresses by a single same-object base delta. Actual runtime addresses remain UNOBSERVED until captured. See `AUDIO_RUNTIME_ADDRESS_RESOLUTION_V77.md` and `data/audio/runtime_address_resolution_v77.json`.

## v78 — executable one-anchor runtime capture plan
v78 converts the v77 same-object runtime-address proof into `tools/build_runtime_capture_plan_v78.py`. Given one debugger-observed runtime address for the verified `object1+0xCDE1` spatial core, it deterministically derives the listener, emitter-table and audio-manager-global addresses and emits the exact read sizes required by the v76 snapshot decoder. A second pass can include the observed manager pointer. No executable patching or quarantined LE-fixup assumptions are used. Bundled self-test addresses are synthetic only.

## v79 — one-command original audio parity processor
v79 composes the v72–v78 evidence chain into `tools/process_original_audio_capture_v79.py`: supplied original manager/emitter dumps establish emitter-slot→pool-index→Miles-handle identity, supplied AIL_DEBUG establishes observed pan/volume, and a supplied F9 capture provides the OpenAzrael reference for the matching room/listener pose. The tool performs exact comparisons and never guesses identity from trace order. Bundled validation is synthetic only; real original-runtime parity remains UNOBSERVED until real captures are supplied. See `AUDIO_ORIGINAL_PARITY_PIPELINE_V79.md`.

## v80 — pose-verified, time-bounded original parity
v80 hardens the v79 parity oracle against two false-positive modes. The original listener position/forward are now read from independent runtime dumps and must match the selected OpenAzrael F9 pose within explicit tolerances. Miles pan/volume must also come from an explicitly bounded trace-line window; a whole-log "latest value" can no longer produce PASS. Missing bounds or pose mismatch return `NOT_EVIDENCE_READY`. See `AUDIO_POSE_VERIFIED_PARITY_V80.md`.

## v81 — DOSBox original-runtime capture kit
v81 packages the v77–v80 runtime evidence path into a read-only, debugger-agnostic capture kit. `tools/build_dosbox_capture_kit_v81.py` generates exact runtime read ranges from one observed CDE1 anchor (and, on the second pass, the observed manager pointer). `tools/validate_capture_bundle_v81.py` enforces exact dump sizes, hashes captured binaries, and checks for the Miles log plus F9 reference capture. Bundle validation is deliberately separate from parity evidence: only the v80 bounded-trace + pose-verified processor can produce a parity PASS.

## v82 — self-locating runtime anchor signature
v82 removes another manual ambiguity from the original-runtime capture path. `tools/derive_runtime_anchor_signature_v82.py` derives and verifies a 16-byte signature for object1+`0xCDE1` from the exact bound demo `R.EXE`. The signature is unique in the rebuilt object-1 image, so a debugger memory search can locate a candidate loaded spatial-core anchor without guessing the DOS load base. Runtime use remains HIGH rather than VERIFIED until a real DOS observation confirms the loaded hit; surrounding bytes must be read back before the v77/v81 address derivation is used. See `AUDIO_RUNTIME_ANCHOR_SIGNATURE_V82.md` and `data/audio/runtime_anchor_signature_v82.json`.

## v83 — automatic runtime-memory anchor location
v83 adds `tools/locate_runtime_audio_anchor_v83.py`. Given a flat DOS memory dump and its linear base, it finds the VERIFIED v82 CDE1 signature, rejects zero/multiple hits, derives the complete v77 runtime address family, and can emit the v81 read-only capture kit automatically. A unique dump hit remains an observed candidate until surrounding bytes are confirmed in the paused original process.

## v84 — one-command original-memory audio parity pipeline

Added `tools/process_memory_audio_capture_v84.py`. A sufficiently broad flat dump of one paused original-game state can now be converted automatically into listener/emitter/manager slices and passed directly to the bounded, pose-verified v80 parity comparator. The tool requires one unique v82 CDE1 signature, checks every derived range against the supplied dump, records SHA-256 provenance, and refuses to infer missing memory. See `AUDIO_ONE_COMMAND_PARITY_V84.md`. Real original-runtime parity remains UNOBSERVED pending a genuine R.EXE capture.

## v85 — concrete DOSBox-X real-capture recipe
v85 grounds the previously debugger-agnostic capture kit in documented DOSBox-X debugger behavior. `tools/build_dosboxx_capture_recipe_v85.py` emits a read-only operator recipe using `MEMDUMPBIN`, preserves the v82/v83 unique-signature and context-confirmation rules, and hands the resulting flat dump to the existing v84 end-to-end processor. No real original-game runtime measurement is claimed; parity remains UNOBSERVED until a genuine R.EXE capture is supplied. See `AUDIO_DOSBOXX_REAL_CAPTURE_V85.md`.

## v86 — activation-ready Classic audio renderer
v86 adds `scripts/classic_miles_renderer_v86.gd` and an opt-in live adapter in `legacy_ambient_audio.gd`. The reconstructed Miles pan/volume values can now drive dedicated Godot audio buses without double-applying Godot 3D attenuation/panning. The gate `enable_unverified_classic_renderer_v86` defaults to false and remains HOLD pending a genuine original-runtime v80/v84 parity PASS. See `AUDIO_CLASSIC_RENDERER_ACTIVATION_V86.md`.

## v87 — evidence-aware gameplay event graph

The playable R7/R8 vertical slice now has a first data-driven gameplay IR (`data/gameplay_event_graph_v87.json`) and runtime dispatcher (`LegacyEvents`). R7 water-switchboard completion and the R8 lens/optical/door/shield chain dispatch state/audio operations through named event graphs instead of duplicating those operations in interaction scripts. Every graph action carries a confidence label; unresolved timer/door-motion semantics remain HOLD. See `GAMEPLAY_EVENT_GRAPH_V87.md`.

## v88 — PUZZLES.DAT importer
Added conservative `tools/import_puzzles_event_ir_v88.py`, `data/puzzles_event_ir_v88.json`, and audit. It converts the proven action byte-pattern corpus into provenance-aware candidate Event IR while explicitly refusing to treat the partial pattern as a complete executable grammar.

## v89 — PUZZLES.DAT false-positive closure
v89 adversarially audited the v88 action scanner and found a deterministic lexical collision: `10 00 Event\0` had been interpreted as opcode `0x45` + token `vent`. The refined importer now rejects and records those occurrences instead of treating them as actions. Bound demo result: 349 v88 raw candidates -> 234 retained candidates + 115 proven lexical collisions. This correction tightens the corpus before record-boundary/grammar reconstruction; retained candidates are still not directly executable.

## v90 — PUZZLES.DAT structural grammar
v90 replaces lexical-only confidence with the first strong structural action-record invariant. 230/234 surviving v89 candidates sit at `FE anchor + 128` and begin `10 00 <opcode> <token>`. These are marked HIGH structural confidence; four unanchored patterns are quarantined as HOLD. Dominant FE spacing is 190 bytes (225 adjacent pairs), but fixed global record length is intentionally not claimed. See `PUZZLES_RECORD_GRAMMAR_V90.md` and `data/puzzles_record_grammar_v90.json`.


## v91 — PUZZLES.DAT action-slot boundary
For the 198 dominant fixed-span records, v91 closes a 62-byte action slot at FE+128..FE+189. Trailing bytes are preserved as opaque residue; semantics remain HOLD. See `PUZZLES_ACTION_SLOT_GRAMMAR_V91.md`.

## v92 — PUZZLES.DAT opaque-residue corpus
v92 groups the 198 structurally clean v91 action slots by opcode and fingerprints only the bytes inside each 62-byte slot after the NUL-terminated token. It computes conservative zero-tail boundaries and ASCII observations without assigning operand semantics. See `PUZZLES_RESIDUE_ANALYSIS_V92.md` and `data/puzzles_residue_analysis_v92.json`.

## v93 — PUZZLES.DAT fixed-field correction
v93 supersedes the assumption that all bytes after the first action token form one semantic residue. Across the 198 HIGH 190-byte records, the 62-byte action slot contains repeatable column-aligned secondary text fields/fragments. Opcode 0x19 is especially strong: all 50 records contain `0x73` at slot +20, while +18 carries a tightly structured small set. Semantics remain HOLD. Runtime opcode-handler offsets are no longer projected onto the disk slot until the PUZZLES.DAT loader/constructor is recovered. See `PUZZLES_FIXED_FIELD_ALIGNMENT_V93.md` and `data/puzzles_fixed_field_evidence_v93.json`.

## v94 — PUZZLES.DAT action-block boundary correction
The dominant 62-byte action slot is now split conservatively into a 32-byte action-bearing prefix and a 30-byte all-zero tail (198/198 records). The 32-byte block is `10 00`, opcode byte, then 29 bytes of opcode-specific payload/storage beginning with the leading token. v92 generic-residue semantics and the stronger v93 fixed-field interpretation are superseded; loader/handler semantics remain HOLD.

## v95 — PUZZLES.DAT payload-family split
v95 refines the v94 payload envelope into two exact serialized families across all 198 dominant records: 189 `COMPACT_18` payloads have bytes +18..+28 zero, while the remaining 9 `EXTENDED_24` payloads have bytes +24..+28 zero; no OTHER layout occurs. All nine extended records contain finite aligned float32 values at payload +12/+16/+20. Their values fit reconstructed demo-room geometry and are therefore PROBABLE legacy XYZ/spatial data; exact loader semantics remain HOLD. See `PUZZLES_PAYLOAD_FAMILIES_V95.md`.

## v96 — structural spatial-record recovery
v96 removes the printable-token population bias from v95. A direct scan of dominant 190-byte `FE` records finds 224 `10 00` action blocks and 15 conservative spatial-like aligned float triplets, recovering six valid records previously hidden by binary prefixes. The repeated R1 and Niamh coordinate clusters are preserved as PROBABLE XYZ; loader semantics remain HOLD. See `PUZZLES_SPATIAL_RECORDS_V96.md`.

## v97 — unbiased structural payload-family closure
v97 generalizes v95's payload families across the full token-independent structural population from v96. All 224 dominant `FE ... FE+190` records with a `10 00` action block at `FE+128` fall into exactly two layouts: 209 `COMPACT_18` and 15 `EXTENDED_24`, with zero OTHER records. Every payload has an exact zero suffix at +24..+28. Independently, the 15 EXTENDED_24 records are exactly the 15 spatial-like records recovered by v96, strengthening the spatial subfamily without upgrading XYZ semantics beyond PROBABLE. See `PUZZLES_STRUCTURAL_PAYLOAD_FAMILIES_V97.md`.

## v98 — PUZZLES.DAT serialized header fingerprint
v98 analyzes the 128-byte pre-action region across all 224 structural records. 100/128 byte columns are invariant, establishing a strong serialized record template. Repeated aligned `0x004xxxxx` dwords are retained as pointer-like PROBABLE evidence only; exact class/vtable semantics remain HOLD pending R.EXE loader recovery. See `PUZZLES_RECORD_HEADER_V98.md` and `data/puzzles_record_header_v98.json`.

## v99 — PUZZLES template-value adversarial audit
v99 adversarially tests the v98 proposal to fingerprint `R.EXE` with invariant `0x004xxxxx` values. All 11 pointer-like invariant dwords are absent byte-exactly from the bound raw R.EXE, so direct raw fingerprinting is SUPERSEDED. The v98 100/128-byte template invariant remains VERIFIED; loader recovery now explicitly requires fixup-aware/code-behavior/runtime evidence. See `PUZZLES_TEMPLATE_VALUE_AUDIT_V99.md`.

## v100 — PUZZLES stride-immediate adversarial audit
Tested the v99 proposal of locating the PUZZLES loader via the verified serialized sizes (190/128/32). A conservative object-1 x86 immediate scan finds numeric candidates but no convincing combined loader fingerprint. The static stride-constant shortcut is therefore rejected as insufficient; loader identity remains HOLD. See `PUZZLES_STRIDE_IMMEDIATE_AUDIT_V100.md` and `data/puzzles_stride_immediate_audit_v100.json`.

## v101 — behavioral file-I/O anchor audit
Static loader hunting moved from numeric stride constants to file-I/O behavior. `R.EXE` has a compact `ReadFlagData` / `GetLine` / `%s.dat` / `r` parsing cluster, while literal `PUZZLES.DAT` is absent. This gives a practical runtime trace anchor but is **not** yet evidence that `ReadFlagData` is the PUZZLES loader. See `PUZZLES_FILEIO_LOADER_TRACE_V101.md`.

## v102 — ReadFlagData caller-chain closure
v102 closes the v101 file-I/O ambiguity. The small string immediates in the `ReadFlagData` source-unit map through a recovered `0x11C558` string-pool base, exposing a direct chain `characte.dat -> character name -> <name>.dat -> ReadFlagData`. The demo independently confirms `CHARACTE.DAT` contains the single name `Niamh` and `NIAMH.DAT` exists. Therefore the v101 `ReadFlagData/%s.dat` path is character flag-data loading, **not valid PUZZLES.DAT loader evidence**. The PUZZLES loader remains HOLD. See `PUZZLES_READFLAGDATA_CALLER_CHAIN_V102.md` and `data/readflagdata_caller_chain_v102.json`.

## v103 — exhaustive direct file-open census
v103 audits the bound executable's complete direct standard-stdio open path before continuing PUZZLES loader hunting. Object 1 has exactly 47 direct calls to the `fopen`-like wrapper at `0x26004`; the lower open routine has only two direct callers. The executable's complete page-backed `.dat` string set contains no `PUZZLES.DAT`, and the only static `%s.dat` xref is the already-closed v102 character path. The audit also recovers `npc%d.dat` strings from the physical tail of object 1's final LE page. A literal/simple static direct-stdio PUZZLES loader route is excluded at HIGH confidence; loader identity remains HOLD. See `PUZZLES_FILEIO_CENSUS_V103.md`.

## v104 — all direct fopen calls classified
v104 classifies all 47 direct calls to `0x26004` using code-local filename/format/diagnostic evidence. Every call belongs to a non-PUZZLES resource, character/NPC, image, audio, configuration, or save/load subsystem; the direct-fopen PUZZLES candidate set is therefore empty at HIGH confidence. In particular, `0x15188/0x15566` are closed as `npc%d.dat` text writer/reader paths and `0x2A6B8` is constrained as a PCX writer by its canonical header construction. Indirect calls and alternative/custom I/O remain untested and become the next target. See `PUZZLES_DIRECT_FOPEN_CLASSIFICATION_V104.md` and `data/direct_fopen_classification_v104.json`.

## v105 — alternative direct-open paths closed
v105 extends the v103/v104 file-I/O census below stdio. Object1 contains exactly six direct calls to the C-runtime `_open`-style wrapper at `0x3CFE2`; all six are constrained to the Miles/AIL driver/file-helper block by the `DIG.INI`/`MDI.INI` source families and shared helper call graph. A conservative DOS `INT 21h` scan finds only three explicit file-open service sites: two inside the known low-level open implementation and one `AX=3D01h` write-only fatal/exit path. No direct PUZZLES read candidate remains in the audited standard/direct mechanisms. Indirect/custom/resource I/O and authoring-time compilation remain HOLD. See `PUZZLES_ALTERNATIVE_OPEN_PATHS_V105.md` and `data/alternative_open_paths_v105.json`.

## v106 — WORLD.DAT runtime serialization closure
v106 pivots from the now-exhausted direct PUZZLES file-open routes to the runtime-loaded `WORLD.DAT`. The loader at object1 `0x36638` opens `world.dat` as `rb`, reads a 30-byte header, and deserializes seven top-level sections. A reconstructed parser based directly on those reader call edges consumes the bound 96,425-byte WORLD.DAT exactly to EOF with section counts `[1303, 12, 37, 3, 101, 8, 15]`. Multiple reader functions have matched writer counterparts, establishing WORLD.DAT as a structured runtime serialization/object database. Adversarially, none of the 133 unique v97 32-byte PUZZLES action blocks appears byte-for-byte in WORLD.DAT, excluding a raw-copy/concatenation model. A PUZZLES/ROOMS -> WORLD authoring/export relationship remains PROBABLE/HOLD until the writer/caller lineage is closed. See `WORLD_RUNTIME_SERIALIZATION_V106.md` and `data/world_runtime_serialization_v106.json`.

## v107 — WORLD / PUZZLES sound-action bridge
v107 adversarially follows the v106 writer-lineage idea and finds that the paired `WORLD.DAT` writer at object1 `0x364A8` has no direct rel32 CALL, direct near-JMP, or canonical LE-fixup reference in the bound demo executable. Its static producer lineage therefore remains HOLD. The live reader remains anchored through `0x1AAED` inside the central initialization path, immediately after the `SGDNAME.DAT` load. The experiment then pivots to WORLD section 6: 40 structurally recovered PUZZLES opcode-`0x28` sound actions are compared against fixed 27-byte WORLD records. **38/40 records** match as a multiset and **all 13/13 PUZZLES sound stems** occur in WORLD records beginning with the same `0x28 + stem + NUL` bytes; all 17 unique WORLD tokens in this record class resolve to shipped WAV assets. Established non-sound opcode families show zero exact opcode+token preservation. This is the first HIGH structural authoring/runtime bridge for a PUZZLES action family while the full compiler remains HOLD. See `WORLD_PUZZLE_SOUND_BRIDGE_V107.md` and `data/world_puzzle_sound_bridge_v107.json`.


## v108 — KG-001 deterministic state-space harness

v108 adds canonical DemoState SHA-256 identity and a source-safe exhaustive puzzle-state explorer. The current R1/R7/R8 logical model contains 63 reachable states and 123 changed transitions; every reachable state can still reach demo completion, with zero modeled softlocks and zero non-success dead ends. This is a source-model milestone only; final KG-001 still requires Godot runtime/headless, save/load, fresh-checkout and manual gates. See `docs/KG001_STATE_SPACE_V108.md`.


## v109 — source-safe Godot headless KG-001 runner

v109 adds schema-validated DemoState restore, logical audio capture-only instrumentation and a Godot headless runner that exercises the real autoload/Event-IR state path without loading `main.tscn` or excluded commercial-derived assets. The source contract is ready; actual Godot runtime execution remains NOT EXECUTED in the current analysis environment. See `docs/KG001_HEADLESS_V109.md`.


## v110 — KG-001 room/trigger runner

v110 prepares asset-backed G04/G05 testing with the real RoomManager path: all four tracked room transitions, locked R1 negative gates, physical trigger inside/outside checks and persistence across room replacement. Missing local room assets are reported as BLOCKED_MISSING_ASSETS. Source contract is PASS; Godot asset-backed execution is NOT EXECUTED here. See `docs/KG001_ROOM_TRIGGER_V110.md`.


## v111 — KG-001 full synthetic demo

v111 adds a complete no-human R1 -> R7 -> R1 -> R8 synthetic playthrough through production interaction scripts and real RoomManager transitions. Direct gameplay flag/puzzle-node injection is rejected by the validator. The runner checks the v108 final-state hash and logical four-sound Event IR stream. Consolidated status is PRE_RUNTIME_READY; actual Godot execution, fresh-checkout verification and manual sanity remain pending. See `docs/KG001_FULL_DEMO_V111.md` and `docs/KG001_STATUS_V111.md`.


## v112 — KG-001 candidate workflow

v112 adds a one-command candidate runner for the full KG-001 pre-release workflow: source validators, Godot discovery, restored-room import, v109/v110/v111 runtime capture, Git cleanliness and repository-safety checks, G09 evidence, optional result promotion, evidence-driven G00-G09 status, and a separate G10 human sanity checklist. Current state is AWAITING_RUNTIME_OR_MANUAL; the demo-known-good-001 tag remains disallowed until every G00-G10 gate is literal PASS. See `docs/KG001_CANDIDATE_RUNNER_V112.md`.
