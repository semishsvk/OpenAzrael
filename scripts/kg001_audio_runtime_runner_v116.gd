extends SceneTree

# KG-001 G06 physical playback-readiness regression for Issue #9.
# This proves resource/load/player routing only. Human audibility and original
# Miles pan/volume parity remain separate G10/forensic evidence.

const REQUIRED_AUDIO := [
    "res://assets/audio/S152V2.WAV",
    "res://assets/audio/S137.WAV",
    "res://assets/audio/S121.WAV",
    "res://assets/audio/799SECDR.WAV",
    "res://assets/audio/S174ELP1.WAV",
    "res://assets/audio/S174ELP2.WAV",
    "res://assets/audio/S186.WAV"
]
const EXPECTED_AMBIENT_COUNTS := {"R1": 2, "R7": 3, "R8": 2}
const EVENT_GRAPH := "R8_LENS_PLACE"
const EVENT_ASSET := "S152V2.WAV"

var failures: Array[String] = []
var checks := 0
var master_capture: AudioEffectCapture
var master_capture_index := -1

func _initialize() -> void:
    call_deferred("_run")

func _check(name: String, condition: bool) -> void:
    checks += 1
    if not condition:
        failures.append(name)

func _settle(frames: int = 3) -> void:
    for _i in range(frames):
        await process_frame

func _install_master_capture(master: int) -> void:
    master_capture = AudioEffectCapture.new()
    master_capture.buffer_length = 1.0
    master_capture_index = AudioServer.get_bus_effect_count(master)
    AudioServer.add_bus_effect(master, master_capture, master_capture_index)
    _check(
        "master_capture_installed",
        AudioServer.get_bus_effect(master, master_capture_index) == master_capture
    )

func _captured_peak() -> Dictionary:
    if master_capture == null:
        return {"frames": 0, "peak": 0.0}
    var available := master_capture.get_frames_available()
    if available <= 0:
        return {"frames": 0, "peak": 0.0}
    var frames: PackedVector2Array = master_capture.get_buffer(available)
    var peak := 0.0
    for frame in frames:
        peak = max(peak, abs(frame.x), abs(frame.y))
    return {"frames": frames.size(), "peak": peak}


func _finish(scene: Node = null) -> void:
    var result := {
        "schema": "openazrael.kg001.audio_runtime",
        "version": 116,
        "status": "PASS" if failures.is_empty() else "FAIL",
        "checks": checks,
        "failed": failures,
        "ambient_counts": EXPECTED_AMBIENT_COUNTS,
        "event_asset": EVENT_ASSET,
        "scope": "G06 physical audio resource/load/player readiness plus non-silent Master-bus capture; human audibility/quality and original Miles parity remain separate"
    }
    print("OPENAZRAEL_KG001_AUDIO_V116 " + JSON.stringify(result))
    var events = root.get_node_or_null("LegacyEvents")
    if events != null and events.has_method("clear_physical_audio"):
        events.call("clear_physical_audio")
    if master_capture_index >= 0:
        var master := AudioServer.get_bus_index("Master")
        if master >= 0 and master_capture_index < AudioServer.get_bus_effect_count(master):
            AudioServer.remove_bus_effect(master, master_capture_index)
        master_capture_index = -1
        master_capture = null
    if scene != null and is_instance_valid(scene):
        scene.queue_free()
    quit(0 if failures.is_empty() else 1)

func _run() -> void:
    _check("ambient_ir_exists", FileAccess.file_exists("res://data/audio/legacy_world_ir.json"))
    for path in REQUIRED_AUDIO:
        _check("resource_exists_" + path.get_file(), ResourceLoader.exists(path))
        if ResourceLoader.exists(path):
            var stream = load(path)
            _check("stream_load_" + path.get_file(), stream is AudioStream)

    var master := AudioServer.get_bus_index("Master")
    _check("master_bus_exists", master >= 0)
    if master >= 0:
        _check("master_bus_not_muted", not AudioServer.is_bus_mute(master))
        _check("master_bus_not_silent", AudioServer.get_bus_volume_db(master) > -79.0)
        _install_master_capture(master)

    if not failures.is_empty():
        _finish()
        return

    var packed = load("res://main.tscn")
    _check("main_scene_load", packed is PackedScene)
    if not packed is PackedScene:
        _finish()
        return

    var scene = (packed as PackedScene).instantiate()
    root.add_child(scene)
    current_scene = scene
    await _settle(4)

    var manager = scene.get_node_or_null("RoomManager")
    var events = root.get_node_or_null("LegacyEvents")
    _check("room_manager_present", manager != null)
    _check("legacy_events_present", events != null)
    if manager == null or events == null:
        _finish(scene)
        return

    for room_id in ["R1", "R7", "R8"]:
        if String(manager.get("current_room_id")) != room_id:
            manager.call("load_room", room_id, false)
            await _settle(3)
        var legacy_audio = manager.get("legacy_audio")
        _check(room_id + "_ambient_node", legacy_audio != null)
        if legacy_audio == null:
            continue
        var snapshots: Array = legacy_audio.call("get_debug_snapshot")
        _check(room_id + "_ambient_count", snapshots.size() == int(EXPECTED_AMBIENT_COUNTS[room_id]))
        for i in range(snapshots.size()):
            var snap: Dictionary = snapshots[i]
            _check("%s_ambient_%d_stream" % [room_id, i], bool(snap.get("stream_valid", false)))
            _check("%s_ambient_%d_playing" % [room_id, i], bool(snap.get("playing", false)))

    events.call("set_capture_only", false)
    events.call("clear_capture")
    events.call("clear_physical_audio")
    _check("event_graph_exists", events.call("has_graph", EVENT_GRAPH))
    if bool(events.call("has_graph", EVENT_GRAPH)):
        if master_capture != null:
            master_capture.clear_buffer()
        events.call("run", EVENT_GRAPH)
        await create_timer(0.35).timeout
        var physical: Array = events.call("physical_audio_snapshot")
        _check("event_logical_emitted", events.call("captured_audio") == [EVENT_ASSET])
        _check("event_physical_player_created", physical.size() == 1)
        if physical.size() == 1:
            var snap: Dictionary = physical[0]
            _check("event_asset_identity", String(snap.get("asset", "")) == EVENT_ASSET)
            _check("event_stream_valid", bool(snap.get("stream_valid", false)))
            _check("event_player_playing", bool(snap.get("playing", false)))
            _check("event_master_bus", String(snap.get("bus", "")) == "Master")
        var captured := _captured_peak()
        _check("master_capture_frames_nonzero", int(captured.get("frames", 0)) > 0)
        _check("master_capture_peak_nonzero", float(captured.get("peak", 0.0)) > 0.000001)

    _finish(scene)
