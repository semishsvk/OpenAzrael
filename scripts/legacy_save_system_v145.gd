extends RefCounted
class_name LegacySaveSystemV145

const SLOT_NAMES := ["FILE ALPHA", "FILE BETA", "FILE GAMMA", "FILE DELTA", "FILE EPSILON"]
const SCHEMA := "openazrael.demo_save"
const VERSION := 145

static func _demo_state() -> Node:
    var tree := Engine.get_main_loop() as SceneTree
    return tree.root.get_node_or_null("DemoState") if tree != null else null

static func _diagnostics() -> Node:
    var tree := Engine.get_main_loop() as SceneTree
    return tree.root.get_node_or_null("CandidateDiagnostics") if tree != null else null

static func _record_event(name: String, payload: Dictionary) -> void:
    var diagnostics := _diagnostics()
    if diagnostics != null and diagnostics.has_method("record_event"):
        diagnostics.call("record_event", name, payload)

static func _reject_load(index: int, reason: String, details: Dictionary = {}) -> bool:
    var payload := {
        "slot": clampi(index, 0, SLOT_NAMES.size() - 1),
        "name": slot_name(index),
        "reason": reason,
    }
    for key in details.keys():
        payload[key] = details[key]
    _record_event("legacy_menu_load_rejected", payload)
    return false

static func slot_path(index: int) -> String:
    return "user://SAVE%d.dat" % clampi(index, 0, SLOT_NAMES.size() - 1)

static func slot_name(index: int) -> String:
    return SLOT_NAMES[clampi(index, 0, SLOT_NAMES.size() - 1)]

static func slot_exists(index: int) -> bool:
    return FileAccess.file_exists(slot_path(index))

static func save_slot(index: int, room_manager: Node, player: CharacterBody3D) -> bool:
    var demo_state := _demo_state()
    if room_manager == null or player == null or demo_state == null:
        return false
    var camera := player.get_node_or_null("Camera3D") as Camera3D
    var pitch := float(player.get("pitch")) if player.get("pitch") != null else (camera.rotation.x if camera != null else 0.0)
    var payload := {
        "schema": SCHEMA,
        "version": VERSION,
        "slot": clampi(index, 0, SLOT_NAMES.size() - 1),
        "slot_name": slot_name(index),
        "state": demo_state.call("canonical_state_payload"),
        "room": String(room_manager.current_room_id),
        "player_position": [player.global_position.x, player.global_position.y, player.global_position.z],
        "player_yaw": player.rotation.y,
        "player_pitch": pitch,
    }
    var file := FileAccess.open(slot_path(index), FileAccess.WRITE)
    if file == null:
        return false
    file.store_string(JSON.stringify(payload))
    file.close()
    _record_event("legacy_menu_save", {"slot": index, "name": slot_name(index), "room": payload["room"]})
    return true

static func load_slot(index: int, room_manager: Node, player: CharacterBody3D) -> bool:
    var demo_state := _demo_state()
    var path := slot_path(index)
    if not FileAccess.file_exists(path):
        return _reject_load(index, "MISSING_SAVE_FILE")
    if room_manager == null or player == null or demo_state == null:
        return _reject_load(index, "RUNTIME_CONTEXT_UNAVAILABLE")

    # Corrupt user saves are an expected rejected input, not an engine error.
    # JSON.parse_string logs an ERROR before our rejection can handle it.
    var parser := JSON.new()
    if parser.parse(FileAccess.get_file_as_string(path)) != OK:
        return _reject_load(index, "INVALID_JSON_OR_ROOT_TYPE")
    var parsed = parser.data
    if not parsed is Dictionary:
        return _reject_load(index, "INVALID_JSON_OR_ROOT_TYPE")
    if String(parsed.get("schema", "")) != SCHEMA:
        return _reject_load(index, "INCOMPATIBLE_SCHEMA", {
            "observed_schema": String(parsed.get("schema", "")),
            "expected_schema": SCHEMA,
        })

    var raw_version = parsed.get("version", null)
    var version_type := typeof(raw_version)
    if version_type != TYPE_INT and version_type != TYPE_FLOAT:
        return _reject_load(index, "MISSING_OR_INVALID_VERSION")
    var observed_version := int(raw_version)
    if observed_version != VERSION:
        return _reject_load(index, "UNSUPPORTED_SAVE_VERSION", {
            "observed_version": observed_version,
            "supported_version": VERSION,
            "migration_available": false,
        })

    var state = parsed.get("state", [])
    if not state is Array:
        return _reject_load(index, "INCOMPATIBLE_STATE_PAYLOAD")
    # DemoState validates the complete canonical payload before mutating its
    # dictionaries, so a rejected payload leaves the live state unchanged.
    if not bool(demo_state.call("restore_canonical_state_payload", state)):
        return _reject_load(index, "INCOMPATIBLE_STATE_PAYLOAD")

    var room := String(parsed.get("room", "R1"))
    room_manager.load_room(room, false)
    room_manager.transition_cooldown = 1.0
    var p = parsed.get("player_position", [])
    if p is Array and p.size() >= 3:
        player.global_position = Vector3(float(p[0]), float(p[1]), float(p[2]))
    player.velocity = Vector3.ZERO
    player.rotation.y = float(parsed.get("player_yaw", 0.0))
    var pitch := float(parsed.get("player_pitch", 0.0))
    player.set("pitch", pitch)
    var camera := player.get_node_or_null("Camera3D") as Camera3D
    if camera != null:
        camera.rotation.x = pitch
    _record_event("legacy_menu_load", {"slot": index, "name": slot_name(index), "room": room, "version": VERSION})
    return true
