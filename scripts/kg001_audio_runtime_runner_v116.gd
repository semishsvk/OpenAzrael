extends SceneTree

# KG-001 G06 physical playback-readiness regression for Issue #9.
# This proves resource/load/player routing only. Human audibility and original
# Miles pan/volume parity remain separate G10/forensic evidence.

const REQUIRED_AUDIO := [
    "res://assets/audio/979TONGS.WAV",
    "res://assets/audio/S152V2.WAV",
    "res://assets/audio/S137.WAV",
    "res://assets/audio/S121.WAV",
    "res://assets/audio/799SECDR.WAV",
    "res://assets/audio/S174ELP1.WAV",
    "res://assets/audio/S174ELP2.WAV",
    "res://assets/audio/S186.WAV"
]
const EXPECTED_AMBIENT_COUNTS := {"R1": 2, "R7": 3, "R8": 2}
const EVENT_PROBES := [
    {"graph":"R7_WELL_TONGS_USE", "asset":"979TONGS.WAV"},
    {"graph":"R7_WATER_SWITCHBOARD_SOLVED", "asset":"S152V2.WAV"}
]

var failures: Array[String] = []
var checks := 0

func _initialize() -> void:
    call_deferred("_run")

func _check(name: String, condition: bool) -> void:
    checks += 1
    if not condition:
        failures.append(name)

func _settle(frames: int = 3) -> void:
    for _i in range(frames):
        await process_frame

func _finish(scene: Node = null) -> void:
    var result := {
        "schema": "openazrael.kg001.audio_runtime",
        "version": 116,
        "status": "PASS" if failures.is_empty() else "FAIL",
        "checks": checks,
        "failed": failures,
        "ambient_counts": EXPECTED_AMBIENT_COUNTS,
        "event_assets": ["979TONGS.WAV", "S152V2.WAV"],
        "scope": "G06 physical audio resource/load/player readiness; human audibility and original Miles parity remain separate"
    }
    print("OPENAZRAEL_KG001_AUDIO_V116 " + JSON.stringify(result))
    var events = root.get_node_or_null("LegacyEvents")
    if events != null and events.has_method("clear_physical_audio"):
        events.call("clear_physical_audio")
    if scene != null and is_instance_valid(scene):
        scene.queue_free()
    # Let queued audio players and the scene release their stream resources.
    await _settle(3)
    # Headless process frames can finish before the audio mixer acknowledges
    # stop/free commands; allow one real mixer cycle before engine shutdown.
    await create_timer(0.15).timeout
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
            _check("%s_ambient_%d_bus" % [room_id, i], String(snap.get("bus", "")) == "OA_Ambient")
            _check("%s_ambient_%d_nonempty_loop" % [room_id, i], int(snap.get("loop_end", 0)) > int(snap.get("loop_begin", 0)))
            _check("%s_ambient_%d_forward_loop" % [room_id, i], int(snap.get("loop_mode", -1)) == AudioStreamWAV.LOOP_FORWARD)

    events.call("set_capture_only", false)
    for probe in EVENT_PROBES:
        var graph_id := String(probe["graph"])
        var asset := String(probe["asset"])
        events.call("clear_capture")
        events.call("clear_physical_audio")
        _check("event_graph_exists_" + graph_id, events.call("has_graph", graph_id))
        if bool(events.call("has_graph", graph_id)):
            events.call("run", graph_id)
            await _settle(1)
            var physical: Array = events.call("physical_audio_snapshot")
            _check("event_logical_emitted_" + asset, events.call("captured_audio") == [asset])
            _check("event_physical_player_created_" + asset, physical.size() == 1)
            if physical.size() == 1:
                var snap: Dictionary = physical[0]
                _check("event_asset_identity_" + asset, String(snap.get("asset", "")) == asset)
                _check("event_stream_valid_" + asset, bool(snap.get("stream_valid", false)))
                _check("event_player_playing_" + asset, bool(snap.get("playing", false)))
                _check("event_master_bus_" + asset, String(snap.get("bus", "")) == "Master")

    _finish(scene)
