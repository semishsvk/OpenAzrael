extends Node3D
# OpenAzrael v46: evidence-aware legacy ambient renderer with verified legacy slot topology.
const IR_PATH := "res://data/audio/legacy_world_ir.json"
const ROOM_TO_LEGACY_ID := {"R1": 0, "R7": 1, "R8": 2}
enum AudioMode { CLASSIC, ENHANCED }
@export var audio_mode: AudioMode = AudioMode.CLASSIC
@export var debug_audio := false
const LEGACY_TOTAL_3D_SLOTS := 7
const LEGACY_AMBIENT_SLOTS := 3
const LEGACY_DYNAMIC_SLOTS := 4
var spawned: Array[AudioStreamPlayer3D] = []
const ClassicParity := preload("res://scripts/classic_3d_parity_backend_v68.gd")
const ClassicMilesRenderer := preload("res://scripts/classic_miles_renderer_v86.gd")
@export_range(0, 127, 1) var parity_master_volume := 99
# Safety gate: remains false until a genuine original-runtime parity capture passes.
@export var enable_unverified_classic_renderer_v86 := false
var classic_bus_by_player: Dictionary = {}
var parity_snapshots: Dictionary = {}

func _process(_delta: float) -> void:
    _update_classic_parity()

func _update_classic_parity() -> void:
    if audio_mode != AudioMode.CLASSIC:
        return
    var camera := get_viewport().get_camera_3d()
    if camera == null:
        return
    var listener_position := camera.global_position
    var listener_forward := -camera.global_transform.basis.z.normalized()
    for p in spawned:
        if not is_instance_valid(p):
            continue
        var result := ClassicParity.evaluate(listener_position, listener_forward, p.global_position, parity_master_volume)
        parity_snapshots[p.name] = result
        p.set_meta("classic_parity_v68", result)
        if enable_unverified_classic_renderer_v86:
            _apply_classic_miles_controls(p, result)

func _ensure_classic_bus(p: AudioStreamPlayer3D) -> int:
    if classic_bus_by_player.has(p.get_instance_id()):
        var existing_name := String(classic_bus_by_player[p.get_instance_id()])
        return AudioServer.get_bus_index(existing_name)
    var bus_name := "OAClassic_%d" % p.get_instance_id()
    AudioServer.add_bus()
    var idx := AudioServer.get_bus_count() - 1
    AudioServer.set_bus_name(idx, bus_name)
    AudioServer.set_bus_send(idx, "Master")
    classic_bus_by_player[p.get_instance_id()] = bus_name
    p.bus = bus_name
    return idx

func _apply_classic_miles_controls(p: AudioStreamPlayer3D, result: Dictionary) -> void:
    if result.get("status", "") != "REFERENCE_V68":
        return
    var pan := int(result.get("pan", 64))
    var volume := int(result.get("volume", 0))
    var idx := _ensure_classic_bus(p)
    ClassicMilesRenderer.configure_bus(idx, pan)
    p.volume_db = ClassicMilesRenderer.miles_volume_to_db(volume)
    # Disable Godot's own distance attenuation while the reconstructed Miles
    # volume law drives gain. Panning is supplied by the dedicated bus panner.
    p.attenuation_model = AudioStreamPlayer3D.ATTENUATION_DISABLED
    p.panning_strength = 0.0
    p.set_meta("renderer", "CLASSIC_MILES_V86_EXPERIMENTAL")
    p.set_meta("renderer_confidence", "HOLD_PENDING_REAL_PARITY")
    p.set_meta("classic_applied_pan", pan)
    p.set_meta("classic_applied_volume", volume)

func _release_classic_buses() -> void:
    var names: Array[String] = []
    for value in classic_bus_by_player.values():
        names.append(String(value))
    # Remove backwards so AudioServer indices cannot shift under us.
    var indices: Array[int] = []
    for bus_name in names:
        var idx := AudioServer.get_bus_index(bus_name)
        if idx > 0:
            indices.append(idx)
    indices.sort()
    indices.reverse()
    for idx in indices:
        AudioServer.remove_bus(idx)
    classic_bus_by_player.clear()

func clear_emitters() -> void:
    for p in spawned:
        if is_instance_valid(p): p.queue_free()
    spawned.clear()
    parity_snapshots.clear()
    _release_classic_buses()

func set_audio_mode(mode: AudioMode) -> void:
    audio_mode = mode
    for p in spawned:
        if is_instance_valid(p): _configure_renderer(p)

func setup_for_room(room_id: String) -> void:
    clear_emitters()
    if not ROOM_TO_LEGACY_ID.has(room_id): return
    var ir = JSON.parse_string(FileAccess.get_file_as_string(IR_PATH))
    if typeof(ir) != TYPE_DICTIONARY: return
    var legacy_id: int = ROOM_TO_LEGACY_ID[room_id]
    for rec in ir.get("audio", {}).get("ambient_emitters", []):
        if int(rec.get("room_id", -1)) != legacy_id: continue
        if spawned.size() >= LEGACY_AMBIENT_SLOTS:
            push_warning("Legacy AMB loader capacity exceeded (verified original capacity = 3)")
            break
        _spawn_emitter(rec, spawned.size())

func _spawn_emitter(rec: Dictionary, legacy_slot: int) -> void:
    var fn := String(rec.get("sample", ""))
    var path := "res://assets/audio/" + fn
    if not ResourceLoader.exists(path):
        push_warning("Missing legacy ambient sample: " + path); return
    var p := AudioStreamPlayer3D.new()
    p.name = "LegacyAmbient_" + fn.get_basename()
    var position_value = rec.get("godot_position")
    if position_value == null:
        position_value = rec.get("legacy_position", [0,0,0])
    p.position = _v3(position_value)
    var stream = load(path)
    if stream is AudioStreamWAV:
        stream = stream.duplicate()
        stream.loop_mode = AudioStreamWAV.LOOP_FORWARD
    p.stream = stream
    p.set_meta("openazrael_provenance", "ORIGINAL_EXPLICIT")
    p.set_meta("legacy_3d_slot", legacy_slot)
    p.set_meta("legacy_slot_class", "AMBIENT_RESERVED_0_2")
    p.set_meta("legacy_runtime_table", "0x227E8 + slot*24")
    p.set_meta("legacy_position", rec.get("legacy_position", []))
    p.set_meta("legacy_source", rec.get("source", {}).get("file", ""))
    p.set_meta("legacy_playback_path", "AMB%d.SND -> parsed filename -> 0xD523 -> 0x1EF44 -> runtime handle -> 0xCDE1 -> Miles pan/volume" % int(rec.get("room_id", -1)))
    p.set_meta("legacy_filename_handle_binding", "HIGH_V43")
    p.set_meta("legacy_loop_count_argument", 1000)
    p.set_meta("legacy_loop_count_confidence", "HIGH_V50")
    p.set_meta("legacy_loop_semantics", "HOLD_MILES_COUNT_SEMANTICS")
    p.set_meta("legacy_initial_pan", 64)
    p.set_meta("legacy_initial_volume", 64)
    p.set_meta("classic_renderer_status", "V67_DEMO_COORDINATES_HIGH__V65_HEADING_HIGH__CALLER_CONSTANT_BINDING_PROVISIONAL")
    add_child(p)
    spawned.append(p)
    _configure_renderer(p)
    p.play()
    if debug_audio:
        print("[OpenAzrael audio] ", p.name, " pos=", p.position, " mode=", AudioMode.keys()[audio_mode])

func _configure_renderer(p: AudioStreamPlayer3D) -> void:
    # R.EXE exposes AIL_set_sample_volume and AIL_set_sample_pan. Until the
    # Play3DSample math is decoded, Classic must remain explicitly approximate.
    if audio_mode == AudioMode.CLASSIC:
        p.attenuation_model = AudioStreamPlayer3D.ATTENUATION_INVERSE_DISTANCE
        p.unit_size = 80.0
        p.max_distance = 700.0
        p.panning_strength = 1.0
        if enable_unverified_classic_renderer_v86:
            p.set_meta("renderer", "CLASSIC_MILES_V86_EXPERIMENTAL")
            p.set_meta("renderer_confidence", "HOLD_PENDING_REAL_PARITY")
        else:
            p.set_meta("renderer", "CLASSIC_FORENSIC_V67_APPROX_RUNTIME__V68_PARITY_SHADOW")
            p.set_meta("renderer_confidence", "HOLD")
    else:
        p.attenuation_model = AudioStreamPlayer3D.ATTENUATION_INVERSE_SQUARE_DISTANCE
        p.unit_size = 100.0
        p.max_distance = 900.0
        p.panning_strength = 1.0
        p.set_meta("renderer", "ENHANCED_SPATIAL_V24")
        p.set_meta("renderer_confidence", "OPENAZRAEL_DESIGN")

func get_debug_snapshot() -> Array[Dictionary]:
    var out: Array[Dictionary] = []
    for p in spawned:
        if not is_instance_valid(p): continue
        out.append({
            "node": p.name,
            "position": [p.position.x,p.position.y,p.position.z],
            "legacy_position": p.get_meta("legacy_position", []),
            "source": p.get_meta("legacy_source", ""),
            "renderer": p.get_meta("renderer", ""),
            "confidence": p.get_meta("renderer_confidence", ""),
            "playing": p.playing,
            "stream_valid": p.stream != null,
            "bus": p.bus,
            "volume_db": p.volume_db,
            "max_distance": p.max_distance,
            "legacy_3d_slot": p.get_meta("legacy_3d_slot", -1),
            "legacy_slot_class": p.get_meta("legacy_slot_class", ""),
            "legacy_loop_count_argument": p.get_meta("legacy_loop_count_argument", -1),
            "legacy_initial_pan": p.get_meta("legacy_initial_pan", -1),
            "legacy_initial_volume": p.get_meta("legacy_initial_volume", -1),
            "classic_parity_v68": p.get_meta("classic_parity_v68", {})
        })
    return out

func _v3(a) -> Vector3:
    return Vector3(float(a[0]), float(a[1]), float(a[2]))
