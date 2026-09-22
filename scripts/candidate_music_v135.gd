extends Node

const MANIFEST_PATH := "res://data/runtime_generated/candidate4_music_manifest_v135.json"
const SILENCE_ID := "BLANK.XMI"

var _manifest: Dictionary = {}
var _player: AudioStreamPlayer
var _manager: Node
var _current_identity := ""
var _last_error := ""

func _ready() -> void:
    _player = AudioStreamPlayer.new()
    _player.name = "CandidateMusicPlayer"
    _player.bus = &"Master"
    add_child(_player)
    _load_manifest()

func _load_manifest() -> void:
    _manifest = {}
    _last_error = ""
    if not FileAccess.file_exists(MANIFEST_PATH):
        return
    var parsed = JSON.parse_string(FileAccess.get_file_as_string(MANIFEST_PATH))
    if not parsed is Dictionary or String(parsed.get("status", "")) != "PASS":
        _last_error = "invalid_candidate4_music_manifest"
        push_error("OpenAzrael Candidate 4: invalid music manifest")
        return
    _manifest = parsed

func bind_room_manager(manager: Node) -> void:
    _manager = manager
    if manager == null:
        return
    var callback := Callable(self, "_on_room_changed")
    if manager.has_signal("room_changed") and not manager.is_connected("room_changed", callback):
        manager.connect("room_changed", callback)
    var room_id = manager.get("current_room_id")
    if room_id != null:
        play_room(String(room_id))

func _on_room_changed(room_id: String) -> void:
    play_room(room_id)

func enabled() -> bool:
    return not _manifest.is_empty()

func play_room(room_id: String) -> void:
    if _manifest.is_empty():
        return
    var by_room: Dictionary = _manifest.get("music_by_room", {})
    if not by_room.has(room_id):
        _fail("missing_music_binding_" + room_id)
        return
    var identity := String(by_room[room_id]).to_upper()
    _current_identity = identity
    if identity == SILENCE_ID:
        _player.stop()
        _player.stream = null
        CandidateDiagnostics.record_event("music_room", {"room": room_id, "xmi": identity, "playing": false})
        return
    var tracks: Dictionary = _manifest.get("tracks", {})
    if not tracks.has(identity):
        _fail("missing_rendered_music_" + identity)
        return
    var meta: Dictionary = tracks[identity]
    var path := String(meta.get("path", ""))
    if path.is_empty() or not ResourceLoader.exists(path):
        _fail("missing_music_resource_" + identity)
        return
    var stream = load(path)
    if not stream is AudioStream:
        _fail("invalid_music_stream_" + identity)
        return
    if stream is AudioStreamOggVorbis:
        (stream as AudioStreamOggVorbis).loop = bool(meta.get("loop", false))
        (stream as AudioStreamOggVorbis).loop_offset = float(meta.get("loop_offset_seconds", 0.0))
    _player.stop()
    _player.stream = stream
    _player.play()
    CandidateDiagnostics.record_event("music_room", {
        "room": room_id,
        "xmi": identity,
        "path": path,
        "loop": bool(meta.get("loop", false)),
        "loop_offset_seconds": float(meta.get("loop_offset_seconds", 0.0)),
        "playing": _player.playing,
    })

func _fail(reason: String) -> void:
    _last_error = reason
    _player.stop()
    push_error("OpenAzrael Candidate 4 music: " + reason)
    CandidateDiagnostics.record_event("music_error", {"reason": reason})

func stop() -> void:
    if is_instance_valid(_player):
        _player.stop()

func debug_snapshot() -> Dictionary:
    var stream_valid := is_instance_valid(_player) and _player.stream is AudioStream
    return {
        "enabled": enabled(),
        "identity": _current_identity,
        "playing": is_instance_valid(_player) and _player.playing,
        "stream_valid": stream_valid,
        "stream_path": String(_player.stream.resource_path) if stream_valid else "",
        "bus": String(_player.bus) if is_instance_valid(_player) else "",
        "last_error": _last_error,
        "loop": bool((_player.stream as AudioStreamOggVorbis).loop) if stream_valid and _player.stream is AudioStreamOggVorbis else false,
        "loop_offset_seconds": float((_player.stream as AudioStreamOggVorbis).loop_offset) if stream_valid and _player.stream is AudioStreamOggVorbis else 0.0,
    }
