extends Node

signal logical_audio_event(filename: String)
signal physical_audio_started(filename: String, player: AudioStreamPlayer)
signal character_animation_requested(request: Dictionary)
signal conversation_requested(request: Dictionary)

const GRAPH_PATH := "res://data/gameplay_event_graph_v87.json"
var graphs: Dictionary = {}
var capture_only := false
var captured_audio_events: Array[String] = []
var physical_audio_players: Array[AudioStreamPlayer] = []

func _ready() -> void:
    var parsed = JSON.parse_string(FileAccess.get_file_as_string(GRAPH_PATH))
    if parsed is Dictionary:
        graphs = parsed.get("graphs", {})
    else:
        push_error("OpenAzrael v87: cannot parse gameplay event graph")

func set_capture_only(enabled: bool) -> void:
    capture_only = enabled

func clear_capture() -> void:
    captured_audio_events.clear()

func captured_audio() -> Array[String]:
    return captured_audio_events.duplicate()

func clear_physical_audio() -> void:
    for p in physical_audio_players:
        if is_instance_valid(p):
            p.stop()
            p.queue_free()
    physical_audio_players.clear()

func physical_audio_snapshot() -> Array[Dictionary]:
    var out: Array[Dictionary] = []
    for p in physical_audio_players:
        if not is_instance_valid(p):
            continue
        out.append({
            "asset": String(p.get_meta("openazrael_audio_asset", "")),
            "playing": p.playing,
            "stream_valid": p.stream != null,
            "bus": p.bus,
            "volume_db": p.volume_db
        })
    return out

func _on_physical_audio_finished(player: AudioStreamPlayer) -> void:
    physical_audio_players.erase(player)
    if is_instance_valid(player):
        player.queue_free()

func has_graph(graph_id: String) -> bool:
    return graphs.has(graph_id)

func run(graph_id: String) -> Array:
    var applied: Array = []
    if not graphs.has(graph_id):
        push_warning("OpenAzrael v87: unknown event graph " + graph_id)
        return applied
    for action in graphs[graph_id].get("actions", []):
        var op := String(action.get("op", ""))
        var key := String(action.get("key", ""))
        match op:
            "set_flag":
                DemoState.set_flag(key, bool(action.get("value", true)))
            "set_puzzle_node":
                DemoState.set_puzzle_node(key, bool(action.get("value", true)))
            "add_inventory":
                DemoState.acquire(key)
            "remove_inventory":
                DemoState.remove(key)
            "play_sound":
                _play_sound(String(action.get("asset", "")))
            "request_character_animation":
                character_animation_requested.emit(action.duplicate(true))
            "request_conversation":
                conversation_requested.emit(action.duplicate(true))
            _:
                push_warning("OpenAzrael v87: unsupported event op " + op)
                continue
        applied.append(action)
    return applied

func _play_sound(filename: String) -> void:
    if filename.is_empty():
        return
    captured_audio_events.append(filename)
    logical_audio_event.emit(filename)
    if capture_only:
        return
    var path := "res://assets/audio/" + filename
    if not ResourceLoader.exists(path):
        push_warning("OpenAzrael v87: missing event sound " + path)
        return
    var p := AudioStreamPlayer.new()
    p.stream = load(path)
    p.set_meta("openazrael_audio_asset", filename)
    var scene := get_tree().current_scene
    if scene == null:
        push_warning("OpenAzrael v87: cannot start event sound without current_scene")
        return
    scene.add_child(p)
    physical_audio_players.append(p)
    p.finished.connect(_on_physical_audio_finished.bind(p))
    p.play()
    physical_audio_started.emit(filename, p)
