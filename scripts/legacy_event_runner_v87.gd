extends Node

const GRAPH_PATH := "res://data/gameplay_event_graph_v87.json"
var graphs: Dictionary = {}

func _ready() -> void:
    var parsed = JSON.parse_string(FileAccess.get_file_as_string(GRAPH_PATH))
    if parsed is Dictionary:
        graphs = parsed.get("graphs", {})
    else:
        push_error("OpenAzrael v87: cannot parse gameplay event graph")

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
            _:
                push_warning("OpenAzrael v87: unsupported event op " + op)
                continue
        applied.append(action)
    return applied

func _play_sound(filename: String) -> void:
    if filename.is_empty():
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
