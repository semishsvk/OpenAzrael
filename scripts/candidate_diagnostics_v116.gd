extends Node

signal event_recorded(entry: Dictionary)

const BUILD_ID := "KG-001 Candidate 1"
const BUILD_CHECKPOINT := "v116-context-v24"
const EVENT_LOG_PATH := "user://openazrael_candidate1_events.jsonl"
const STATE_DUMP_PREFIX := "user://openazrael_kg001_state_dump_"

const REQUIRED_CORE_RESOURCES := [
    "res://assets/rooms/R1.glb",
    "res://assets/rooms/R7.glb",
    "res://assets/rooms/R8.glb",
    "res://data/xaf_trigger_evidence.json",
    "res://data/gameplay_event_graph_v87.json"
]

# Golden Event-IR stream used by the KG-001 demo route. Ambient/classic parity
# has its own evidence track and is intentionally not promoted here.
const REQUIRED_CANDIDATE_AUDIO := [
    "res://assets/audio/S152V2.WAV",
    "res://assets/audio/S137.WAV",
    "res://assets/audio/S121.WAV",
    "res://assets/audio/799SECDR.WAV"
]

var last_event: Dictionary = {}
var last_trigger := "(none)"
var last_audio := "(none)"
var startup_errors: Array[String] = []
var event_sequence := 0
var file_logging_enabled := false
var _trigger_states: Dictionary = {}

func _ready() -> void:
    file_logging_enabled = DisplayServer.get_name() != "headless"
    DemoState.inventory_changed.connect(_on_inventory_changed)
    DemoState.flag_changed.connect(_on_flag_changed)
    DemoState.puzzle_node_changed.connect(_on_puzzle_node_changed)
    LegacyEvents.logical_audio_event.connect(_on_logical_audio_event)
    record_event("diagnostics_ready", {
        "build_id": BUILD_ID,
        "checkpoint": BUILD_CHECKPOINT,
        "file_logging": file_logging_enabled
    })

func _sorted_keys(source: Dictionary) -> Array[String]:
    var out: Array[String] = []
    for key in source.keys():
        out.append(String(key))
    out.sort()
    return out

func _append_event_log(entry: Dictionary) -> void:
    if not file_logging_enabled:
        return
    var f: FileAccess
    if FileAccess.file_exists(EVENT_LOG_PATH):
        f = FileAccess.open(EVENT_LOG_PATH, FileAccess.READ_WRITE)
        if f != null:
            f.seek_end()
    else:
        f = FileAccess.open(EVENT_LOG_PATH, FileAccess.WRITE)
    if f == null:
        push_warning("OpenAzrael Candidate Diagnostics: cannot open event log " + EVENT_LOG_PATH)
        return
    f.store_line(JSON.stringify(entry))
    f.flush()

func record_event(kind: String, data: Dictionary = {}) -> void:
    event_sequence += 1
    var entry := {
        "seq": event_sequence,
        "unix_time": Time.get_unix_time_from_system(),
        "ticks_msec": Time.get_ticks_msec(),
        "kind": kind,
        "data": data.duplicate(true),
        "state_hash": DemoState.canonical_state_hash()
    }
    last_event = entry
    _append_event_log(entry)
    event_recorded.emit(entry)

func _on_inventory_changed() -> void:
    record_event("inventory_changed", {"inventory": _sorted_keys(DemoState.inventory)})

func _on_flag_changed(flag_name: String, value: bool) -> void:
    record_event("flag_changed", {"flag": flag_name, "value": value})

func _on_puzzle_node_changed(node_name: String, value: bool) -> void:
    record_event("puzzle_node_changed", {"node": node_name, "value": value})

func _on_logical_audio_event(filename: String) -> void:
    last_audio = filename
    record_event("logical_audio", {"asset": filename})

func record_interaction(target_name: String) -> void:
    record_event("interaction", {"target": target_name})

func record_room_loaded(room_id: String) -> void:
    _trigger_states.clear()
    record_event("room_loaded", {"room": room_id})

func record_transition(source_room: String, trigger_name: String, destination_room: String) -> void:
    record_event("room_transition", {
        "source_room": source_room,
        "trigger": trigger_name,
        "destination_room": destination_room
    })

func observe_trigger(room_id: String, trigger_name: String, inside: bool) -> void:
    var key := room_id + ":" + trigger_name
    if _trigger_states.has(key) and bool(_trigger_states[key]) == inside:
        return
    _trigger_states[key] = inside
    var edge := "ENTER" if inside else "EXIT"
    last_trigger = "%s %s/%s" % [edge, room_id, trigger_name]
    record_event("trigger_" + ("enter" if inside else "exit"), {
        "room": room_id,
        "trigger": trigger_name
    })

func _resource_exists(path: String) -> bool:
    if path.ends_with(".json"):
        return FileAccess.file_exists(path)
    return ResourceLoader.exists(path)

func validate_required_resources(require_audio: bool) -> Array[String]:
    var missing: Array[String] = []
    for path in REQUIRED_CORE_RESOURCES:
        if not _resource_exists(path):
            missing.append(path)
    if require_audio:
        for path in REQUIRED_CANDIDATE_AUDIO:
            if not _resource_exists(path):
                missing.append(path)
    return missing

func fail_fast_if_required_resources_missing(require_audio: bool) -> bool:
    startup_errors = validate_required_resources(require_audio)
    if startup_errors.is_empty():
        record_event("candidate_asset_validation", {
            "status": "PASS",
            "audio_required": require_audio
        })
        return true
    for path in startup_errors:
        push_error("OpenAzrael KG-001 Candidate 1 missing required resource: " + path)
    record_event("candidate_asset_validation", {
        "status": "FAIL",
        "audio_required": require_audio,
        "missing": startup_errors
    })
    return false

func last_event_text() -> String:
    if last_event.is_empty():
        return "(none)"
    return "#%d %s" % [int(last_event.get("seq", 0)), String(last_event.get("kind", "?"))]

func dump_state(room_id: String, player_position: Vector3) -> String:
    var stamp := int(Time.get_unix_time_from_system())
    var path := "%s%d_%04d.json" % [STATE_DUMP_PREFIX, stamp, event_sequence % 10000]
    var payload := {
        "schema": "openazrael.kg001.runtime_state_dump",
        "version": 116,
        "build_id": BUILD_ID,
        "checkpoint": BUILD_CHECKPOINT,
        "room": room_id,
        "player_position": [player_position.x, player_position.y, player_position.z],
        "canonical_state_payload": DemoState.canonical_state_payload(),
        "canonical_state_hash": DemoState.canonical_state_hash(),
        "last_event": last_event,
        "last_trigger": last_trigger,
        "last_audio": last_audio,
        "event_log_path": EVENT_LOG_PATH
    }
    var f := FileAccess.open(path, FileAccess.WRITE)
    if f == null:
        push_error("OpenAzrael Candidate Diagnostics: state dump failed: " + path)
        return ""
    f.store_string(JSON.stringify(payload, "  ") + "\n")
    f.flush()
    record_event("state_dump", {"path": path, "dump_hash": payload["canonical_state_hash"]})
    print("OpenAzrael KG-001 state dump: ", path)
    return path
