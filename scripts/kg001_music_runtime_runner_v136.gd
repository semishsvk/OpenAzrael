extends SceneTree

const MANIFEST_PATH := "res://data/runtime_generated/candidate4_music_manifest_v135.json"
var failures: Array[String] = []
var checks := 0

func _initialize() -> void:
    call_deferred("_run")

func _check(name: String, condition: bool) -> void:
    checks += 1
    if not condition:
        failures.append(name)

func _settle(frames := 4) -> void:
    for _i in range(frames):
        await process_frame

func _run() -> void:
    _check("manifest_exists", FileAccess.file_exists(MANIFEST_PATH))
    if not FileAccess.file_exists(MANIFEST_PATH):
        _finish({})
        return
    var manifest = JSON.parse_string(FileAccess.get_file_as_string(MANIFEST_PATH))
    _check("manifest_valid", manifest is Dictionary and String(manifest.get("status", "")) == "PASS")
    var music = root.get_node_or_null("CandidateMusic")
    _check("candidate_music_autoload", music != null)
    if music == null or not manifest is Dictionary:
        _finish(manifest if manifest is Dictionary else {})
        return
    _check("music_enabled", bool(music.call("enabled")))
    var by_room: Dictionary = manifest.get("music_by_room", {})
    var tracks: Dictionary = manifest.get("tracks", {})
    _check("rendered_track_set_nonempty", tracks.size() > 0)
    for identity in tracks.keys():
        var meta: Dictionary = tracks[identity]
        var path := String(meta.get("path", ""))
        _check("corpus_resource_exists_" + String(identity), ResourceLoader.exists(path))
        if ResourceLoader.exists(path):
            var stream = load(path)
            _check("corpus_stream_load_" + String(identity), stream is AudioStreamOggVorbis)
            if stream is AudioStreamOggVorbis:
                _check("corpus_duration_" + String(identity), float((stream as AudioStreamOggVorbis).get_length()) > 0.0)
    for room_id in ["R1", "R7", "R8"]:
        _check("binding_" + room_id, by_room.has(room_id))
        if not by_room.has(room_id):
            continue
        var identity := String(by_room[room_id]).to_upper()
        music.call("play_room", room_id)
        await _settle(6)
        var snap: Dictionary = music.call("debug_snapshot")
        _check(room_id + "_identity", String(snap.get("identity", "")) == identity)
        _check(room_id + "_no_error", String(snap.get("last_error", "")).is_empty())
        if identity == "BLANK.XMI":
            _check(room_id + "_explicit_silence", not bool(snap.get("playing", true)))
            continue
        _check(room_id + "_track_manifest", tracks.has(identity))
        if not tracks.has(identity):
            continue
        var meta: Dictionary = tracks[identity]
        var path := String(meta.get("path", ""))
        _check(room_id + "_resource_exists", ResourceLoader.exists(path))
        _check(room_id + "_stream_valid", bool(snap.get("stream_valid", false)))
        _check(room_id + "_playing", bool(snap.get("playing", false)))
        _check(room_id + "_music_bus", String(snap.get("bus", "")) == "OA_Music")
        _check(room_id + "_loop", bool(snap.get("loop", false)) == bool(meta.get("loop", false)))
        _check(room_id + "_loop_offset", absf(float(snap.get("loop_offset_seconds", 0.0)) - float(meta.get("loop_offset_seconds", 0.0))) < 0.01)
    music.call("stop")
    _finish(manifest)

func _finish(manifest: Dictionary) -> void:
    var result := {
        "schema": "openazrael.kg001.candidate4_music_runtime",
        "version": 136,
        "status": "PASS" if failures.is_empty() else "FAIL",
        "checks": checks,
        "failed": failures,
        "rooms": ["R1", "R7", "R8"],
        "manifest_schema": String(manifest.get("schema", "")),
        "scope": "Godot resource/load/player/loop routing for Candidate 4 rendered music; G10 remains the human audibility gate"
    }
    print("OPENAZRAEL_KG001_MUSIC_V136 " + JSON.stringify(result))
    await process_frame
    quit(0 if failures.is_empty() else 1)
