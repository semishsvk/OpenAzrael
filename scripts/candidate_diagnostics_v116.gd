extends Node

signal event_recorded(entry: Dictionary)
signal bug_report_created(path: String)

const BUILD_ID := "KG-001 Candidate 3"
const BUILD_CHECKPOINT := "v116-context-v32"
const EVENT_LOG_PATH := "user://openazrael_candidate3_events.jsonl"
const STATE_DUMP_PREFIX := "user://openazrael_kg001_state_dump_"
const BUG_REPORT_PREFIX := "user://openazrael_bugreport_"
const BUG_REPORT_SCHEMA := "openazrael.bug_report"
const BUG_REPORT_SCHEMA_VERSION := 2
const RUNTIME_BUILD_IDENTITY_PATH := "res://data/runtime_build_identity.json"
const BUG_REPORT_EVENT_TAIL_LINES := 500

const REQUIRED_CORE_RESOURCES := [
    "res://assets/rooms/R1.glb",
    "res://assets/rooms/R7.glb",
    "res://assets/rooms/R8.glb",
    "res://data/xaf_trigger_evidence.json",
    "res://data/gameplay_event_graph_v87.json",
    "res://data/audio/legacy_world_ir.json"
]

# Physical Candidate audio resources required for G06 readiness. Original
# Miles pan/volume parity remains a separate forensic HOLD.
const REQUIRED_CANDIDATE_AUDIO := [
    "res://assets/audio/979TONGS.WAV",
    "res://assets/audio/S152V2.WAV",
    "res://assets/audio/S137.WAV",
    "res://assets/audio/S121.WAV",
    "res://assets/audio/799SECDR.WAV",
    "res://assets/audio/S174ELP1.WAV",
    "res://assets/audio/S174ELP2.WAV",
    "res://assets/audio/S186.WAV"
]

var last_event: Dictionary = {}
var last_trigger := "(none)"
var last_audio := "(none)"
var startup_errors: Array[String] = []
var event_sequence := 0
var file_logging_enabled := false
var _trigger_states: Dictionary = {}
var last_trigger_room := ""
var last_trigger_name := ""
var last_trigger_edge := ""
var last_bug_report := ""
var _bug_report_capture_in_progress := false

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
    var f: FileAccess = null
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
    if not _trigger_states.has(key):
        _trigger_states[key] = inside
        if not inside:
            return
    elif bool(_trigger_states[key]) == inside:
        return
    else:
        _trigger_states[key] = inside
    var edge := "ENTER" if inside else "EXIT"
    last_trigger = "%s %s/%s" % [edge, room_id, trigger_name]
    last_trigger_room = room_id
    last_trigger_name = trigger_name
    last_trigger_edge = edge
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
        push_error("OpenAzrael KG-001 Candidate 3 missing required resource: " + path)
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


# v116-context-v32: observational one-key bug-report capture.
# Reads diagnostics/runtime state only; no gameplay mutator is called.
func stable_room_id(room_id: String) -> String:
    return "ROOM:" + (room_id if not room_id.is_empty() else "UNKNOWN")

func stable_trigger_id(room_id: String, trigger_name: String) -> String:
    if trigger_name.is_empty():
        return ""
    return "TRG:%s:%s" % [room_id if not room_id.is_empty() else "UNKNOWN", trigger_name]

func stable_puzzle_id(node_name: String) -> String:
    return "PUZ:" + node_name

func stable_flag_id(flag_name: String) -> String:
    return "FLAG:" + flag_name

func stable_item_id(item_name: String) -> String:
    return "ITEM:" + item_name

func _active_entity_ids() -> Dictionary:
    var items: Array[String] = []
    var flags: Array[String] = []
    var puzzles: Array[String] = []
    for key in _sorted_keys(DemoState.inventory):
        if bool(DemoState.inventory.get(key, false)):
            items.append(stable_item_id(key))
    for key in _sorted_keys(DemoState.flags):
        if bool(DemoState.flags.get(key, false)):
            flags.append(stable_flag_id(key))
    for key in _sorted_keys(DemoState.puzzle_nodes):
        if bool(DemoState.puzzle_nodes.get(key, false)):
            puzzles.append(stable_puzzle_id(key))
    return {"items": items, "flags": flags, "puzzles": puzzles}

func _vec3_payload(value: Vector3) -> Array:
    return [value.x, value.y, value.z]

func _ray_hit_payload(hit: Dictionary, player_y: float) -> Dictionary:
    if hit.is_empty():
        return {"hit": false}
    var collider = hit.get("collider")
    var position: Vector3 = hit.get("position", Vector3.ZERO)
    var normal: Vector3 = hit.get("normal", Vector3.ZERO)
    return {
        "hit": true,
        "collider_name": String(collider.name) if collider is Node else "",
        "collider_path": String(collider.get_path()) if collider is Node else "",
        "collider_type": collider.get_class() if collider is Object else "",
        "position": _vec3_payload(position),
        "normal": _vec3_payload(normal),
        "vertical_delta_from_player": position.y - player_y,
        "shape_index": int(hit.get("shape", -1))
    }

func _ray_probe(
    scene: Node3D,
    player: CharacterBody3D,
    from: Vector3,
    to: Vector3
) -> Dictionary:
    var query := PhysicsRayQueryParameters3D.create(from, to, 1)
    query.exclude = [player.get_rid()]
    query.hit_back_faces = true
    return scene.get_world_3d().direct_space_state.intersect_ray(query)

func _nearby_collision_bodies(
    scene: Node3D,
    player: CharacterBody3D,
    radius: float = 96.0
) -> Array:
    var sphere := SphereShape3D.new()
    sphere.radius = radius
    var query := PhysicsShapeQueryParameters3D.new()
    query.shape = sphere
    query.transform = Transform3D(Basis.IDENTITY, player.global_position)
    query.collision_mask = 1
    query.exclude = [player.get_rid()]
    var hits := scene.get_world_3d().direct_space_state.intersect_shape(query, 32)
    var rows: Array = []
    var seen: Dictionary = {}
    for hit in hits:
        if not (hit is Dictionary):
            continue
        var collider = hit.get("collider")
        if not (collider is CollisionObject3D):
            continue
        var id := (collider as CollisionObject3D).get_instance_id()
        if seen.has(id):
            continue
        seen[id] = true
        var body := collider as CollisionObject3D
        rows.append({
            "name": String(body.name),
            "path": String(body.get_path()),
            "type": body.get_class(),
            "collision_layer": int(body.collision_layer),
            "collision_mask": int(body.collision_mask),
            "transform_origin": _vec3_payload(body.global_position),
            "origin_distance_to_player": body.global_position.distance_to(
                player.global_position
            )
        })
    rows.sort_custom(
        func(a: Dictionary, b: Dictionary) -> bool:
            return float(a["origin_distance_to_player"]) < float(b["origin_distance_to_player"])
    )
    if rows.size() > 12:
        rows.resize(12)
    return rows

func _physics_context(
    scene: Node3D,
    player: CharacterBody3D
) -> Dictionary:
    var pos := player.global_position
    var support_below := _ray_probe(
        scene,
        player,
        pos + Vector3.UP * 2.0,
        pos + Vector3.DOWN * 512.0
    )
    var column_probe := _ray_probe(
        scene,
        player,
        Vector3(pos.x, pos.y + 128.0, pos.z),
        Vector3(pos.x, pos.y - 512.0, pos.z)
    )
    var slide_colliders: Array = []
    for index in range(player.get_slide_collision_count()):
        var collision := player.get_slide_collision(index)
        if collision == null:
            continue
        var collider = collision.get_collider()
        slide_colliders.append({
            "name": String(collider.name) if collider is Node else "",
            "type": collider.get_class() if collider is Object else "",
            "normal": _vec3_payload(collision.get_normal()),
            "position": _vec3_payload(collision.get_position())
        })
    return {
        "velocity": _vec3_payload(player.velocity),
        "is_on_floor": player.is_on_floor(),
        "floor_normal": _vec3_payload(player.get_floor_normal()),
        "up_direction": _vec3_payload(player.up_direction),
        "floor_snap_length": player.floor_snap_length,
        "floor_max_angle": player.floor_max_angle,
        "safe_margin": player.safe_margin,
        "collision_layer": int(player.collision_layer),
        "collision_mask": int(player.collision_mask),
        "slide_collision_count": player.get_slide_collision_count(),
        "slide_colliders": slide_colliders,
        "support_below": _ray_hit_payload(support_below, pos.y),
        "column_probe": _ray_hit_payload(column_probe, pos.y),
        "nearby_collision_bodies_radius": 96.0,
        "nearby_collision_bodies": _nearby_collision_bodies(
            scene, player, 96.0
        )
    }

func _runtime_build_identity() -> Dictionary:
    if not FileAccess.file_exists(RUNTIME_BUILD_IDENTITY_PATH):
        return {"status": "UNAVAILABLE"}
    var parsed = JSON.parse_string(
        FileAccess.get_file_as_string(RUNTIME_BUILD_IDENTITY_PATH)
    )
    if not (parsed is Dictionary):
        return {"status": "INVALID"}
    return parsed

func _runtime_context() -> Dictionary:
    var room_id := "UNKNOWN"
    var player_position := Vector3.ZERO
    var physics: Dictionary = {"status": "UNAVAILABLE"}
    var scene := get_tree().current_scene
    if scene != null:
        var room_manager := scene.get_node_or_null("RoomManager")
        if room_manager != null:
            var value = room_manager.get("current_room_id")
            if value != null:
                room_id = String(value)
        var player := scene.get_node_or_null("Player")
        if player is CharacterBody3D and scene is Node3D:
            player_position = (player as CharacterBody3D).global_position
            physics = _physics_context(
                scene as Node3D,
                player as CharacterBody3D
            )
        elif player is Node3D:
            player_position = (player as Node3D).global_position
    return {
        "room_id": room_id,
        "room_entity_id": stable_room_id(room_id),
        "player_position": [player_position.x, player_position.y, player_position.z],
        "physics": physics
    }

func _system_info() -> Dictionary:
    var screen_size := DisplayServer.screen_get_size()
    return {
        "os_name": OS.get_name(),
        "os_version": OS.get_version(),
        "locale": OS.get_locale(),
        "godot": Engine.get_version_info(),
        "display_server": DisplayServer.get_name(),
        "screen_size": [screen_size.x, screen_size.y],
        "runtime_build_identity": _runtime_build_identity()
    }

func _event_log_tail(max_lines: int = BUG_REPORT_EVENT_TAIL_LINES) -> String:
    if not FileAccess.file_exists(EVENT_LOG_PATH):
        return ""
    var content := FileAccess.get_file_as_string(EVENT_LOG_PATH)
    var lines := content.split("\n", false)
    var start: int = max(0, lines.size() - max_lines)
    var out := ""
    for i in range(start, lines.size()):
        out += String(lines[i]) + "\n"
    return out

func _zip_add_bytes(packer, path: String, bytes: PackedByteArray) -> bool:
    if packer.start_file(path) != OK:
        return false
    var write_error = packer.write_file(bytes)
    var close_error = packer.close_file()
    return write_error == OK and close_error == OK

func _zip_add_text(packer, path: String, content: String) -> bool:
    return _zip_add_bytes(packer, path, content.to_utf8_buffer())

func _capture_screenshot_png() -> PackedByteArray:
    if DisplayServer.get_name() == "headless":
        return PackedByteArray()
    var viewport := get_viewport()
    if viewport == null:
        return PackedByteArray()
    var image := viewport.get_texture().get_image()
    if image == null or image.is_empty():
        return PackedByteArray()
    return image.save_png_to_buffer()

func _state_snapshot(context: Dictionary, last_game_event: Dictionary) -> Dictionary:
    return {
        "schema": "openazrael.kg001.runtime_state_snapshot",
        "version": 2,
        "build_id": BUILD_ID,
        "checkpoint": BUILD_CHECKPOINT,
        "room": context.get("room_id", "UNKNOWN"),
        "room_entity_id": context.get("room_entity_id", "ROOM:UNKNOWN"),
        "player_position": context.get("player_position", [0.0, 0.0, 0.0]),
        "physics": context.get("physics", {"status":"UNAVAILABLE"}),
        "canonical_state_payload": DemoState.canonical_state_payload(),
        "canonical_state_hash": DemoState.canonical_state_hash(),
        "active_entity_ids": _active_entity_ids(),
        "last_game_event": last_game_event,
        "last_trigger": {
            "text": last_trigger,
            "room": last_trigger_room,
            "name": last_trigger_name,
            "edge": last_trigger_edge,
            "entity_id": stable_trigger_id(last_trigger_room, last_trigger_name)
        },
        "last_audio": last_audio
    }

func _bug_report_text(report: Dictionary) -> String:
    var lines := [
        "OpenAzrael Bug Report",
        "",
        "Build: " + String(report.get("build_id", "")),
        "Checkpoint: " + String(report.get("checkpoint", "")),
        "Room: " + String(report.get("room", "")),
        "Room ID: " + String(report.get("room_entity_id", "")),
        "Trigger ID: " + String(report.get("trigger_entity_id", "")),
        "State SHA-256: " + String(report.get("canonical_state_hash", "")),
        "Source commit: " + String(report.get("source_commit", "UNAVAILABLE")),
        "Support collider: " + String(
            report.get("physics", {}).get("column_probe", {}).get(
                "collider_name", "(none)"
            )
        ),
        "",
        "Fill these fields in the GitHub issue:",
        "Summary:",
        "Steps to reproduce:",
        "Expected behaviour:",
        "Actual behaviour:",
        "Reproducibility: Always / Often / Sometimes / Once",
        "Severity: Critical / Major / Minor / Cosmetic",
        "",
        "Attach this ZIP to the issue. Do not attach excluded commercial game assets."
    ]
    var out := ""
    for line in lines:
        out += String(line) + "\n"
    return out

func capture_bug_report() -> String:
    if _bug_report_capture_in_progress:
        return ""
    if DisplayServer.get_name() == "headless":
        push_warning("OpenAzrael bug report capture is disabled in headless mode.")
        return ""

    _bug_report_capture_in_progress = true
    var last_game_event := last_event.duplicate(true)
    var context := _runtime_context()
    record_event("bug_report_capture_requested", {
        "room": context.get("room_id", "UNKNOWN"),
        "room_entity_id": context.get("room_entity_id", "ROOM:UNKNOWN")
    })

    var stamp := int(Time.get_unix_time_from_system())
    var suffix := event_sequence % 10000
    var base := "%s%d_%04d" % [BUG_REPORT_PREFIX, stamp, suffix]
    var zip_path := base + ".zip"
    var screenshot_bytes := _capture_screenshot_png()
    var screenshot_ok := not screenshot_bytes.is_empty()
    var system_info := _system_info()
    var state := _state_snapshot(context, last_game_event)
    var report := {
        "schema": BUG_REPORT_SCHEMA,
        "schema_version": BUG_REPORT_SCHEMA_VERSION,
        "build_id": BUILD_ID,
        "checkpoint": BUILD_CHECKPOINT,
        "created_unix": stamp,
        "repository": "semishsvk/OpenAzrael",
        "room": context.get("room_id", "UNKNOWN"),
        "room_entity_id": context.get("room_entity_id", "ROOM:UNKNOWN"),
        "trigger_entity_id": stable_trigger_id(last_trigger_room, last_trigger_name),
        "player_position": context.get("player_position", [0.0, 0.0, 0.0]),
        "physics": context.get("physics", {"status":"UNAVAILABLE"}),
        "source_commit": String(
            system_info.get("runtime_build_identity", {}).get(
                "commit_sha", "UNAVAILABLE"
            )
        ),
        "canonical_state_hash": DemoState.canonical_state_hash(),
        "last_game_event": last_game_event,
        "last_trigger": last_trigger,
        "last_audio": last_audio,
        "event_log_source": EVENT_LOG_PATH,
        "event_log_tail_limit": BUG_REPORT_EVENT_TAIL_LINES,
        "screenshot_included": screenshot_ok,
        "severity": "UNCLASSIFIED",
        "reproducibility": "UNCLASSIFIED",
        "summary": "",
        "steps_to_reproduce": [],
        "expected_behaviour": "",
        "actual_behaviour": ""
    }

    var packer := ZIPPacker.new()
    var open_error := packer.open(zip_path)
    if open_error != OK:
        _bug_report_capture_in_progress = false
        push_error("OpenAzrael bug report ZIP open failed: " + zip_path)
        return ""

    var included: Array[String] = []
    var entry_errors: Array[String] = []
    var entries := [
        ["report.json", JSON.stringify(report, "  ") + "\n"],
        ["report.txt", _bug_report_text(report)],
        ["state.json", JSON.stringify(state, "  ") + "\n"],
        ["system_info.json", JSON.stringify(system_info, "  ") + "\n"],
        ["events_tail.jsonl", _event_log_tail()]
    ]
    for entry in entries:
        if _zip_add_text(packer, String(entry[0]), String(entry[1])):
            included.append(String(entry[0]))
        else:
            entry_errors.append(String(entry[0]))

    if screenshot_ok:
        if _zip_add_bytes(packer, "screenshot.png", screenshot_bytes):
            included.append("screenshot.png")
        else:
            entry_errors.append("screenshot.png")

    var manifest := {
        "schema": "openazrael.bug_report_manifest",
        "version": 2,
        "build_id": BUILD_ID,
        "checkpoint": BUILD_CHECKPOINT,
        "files": included,
        "entry_errors": entry_errors,
        "source_safe": true,
        "commercial_assets_included": false
    }
    if _zip_add_text(packer, "manifest.json", JSON.stringify(manifest, "  ") + "\n"):
        included.append("manifest.json")
    else:
        entry_errors.append("manifest.json")
    packer.close()

    last_bug_report = zip_path
    _bug_report_capture_in_progress = false
    record_event("bug_report_created", {
        "path": zip_path,
        "room": context.get("room_id", "UNKNOWN"),
        "room_entity_id": context.get("room_entity_id", "ROOM:UNKNOWN"),
        "state_hash": report["canonical_state_hash"],
        "entry_errors": entry_errors
    })
    bug_report_created.emit(zip_path)
    print("OpenAzrael bug report package: ", zip_path)
    return zip_path

func _unhandled_key_input(event: InputEvent) -> void:
    if not event.pressed or event.echo:
        return
    if event.keycode == KEY_F11:
        capture_bug_report()
        get_viewport().set_input_as_handled()
