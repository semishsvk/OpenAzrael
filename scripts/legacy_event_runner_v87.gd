extends Node

signal logical_audio_event(filename: String)
signal logical_audio_event_detail(detail: Dictionary)

var current_graph_id := ""
var current_action: Dictionary = {}

const GRAPH_PATH := "res://data/gameplay_event_graph_v87.json"
var graphs: Dictionary = {}
var capture_only := false
var captured_audio_events: Array[String] = []

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

func has_graph(graph_id: String) -> bool:
    return graphs.has(graph_id)

func run(graph_id: String) -> Array:
    var applied: Array = []
    current_graph_id = graph_id
    if not graphs.has(graph_id):
        push_warning("OpenAzrael v87: unknown event graph " + graph_id)
        return applied
    for action in graphs[graph_id].get("actions", []):
        current_action = action
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
            _:
                push_warning("OpenAzrael v87: unsupported event op " + op)
                continue
        applied.append(action)
    current_action = {}
    current_graph_id = ""
    return applied

func _play_sound(filename: String) -> void:
    if filename.is_empty():
        return
    captured_audio_events.append(filename)
    logical_audio_event.emit(filename)
    logical_audio_event_detail.emit({
        "graph_id": current_graph_id,
        "asset": filename,
        "semantic": String(current_action.get("semantic", "")),
        "confidence": String(current_action.get("confidence", "HOLD")),
        "provenance": graphs.get(current_graph_id, {}).get("source", []),
        "emitter_id": "dynamic." + current_graph_id.to_lower(),
        "sound_id": "event." + filename.get_basename().to_lower()
    })
    if capture_only:
        return
    var path := "res://assets/audio/" + filename
    if not ResourceLoader.exists(path):
        push_warning("OpenAzrael v87: missing event sound " + path)
        return
    var p := AudioStreamPlayer.new()
    p.stream = load(path)
    get_tree().current_scene.add_child(p)
    p.finished.connect(p.queue_free)
    p.play()
