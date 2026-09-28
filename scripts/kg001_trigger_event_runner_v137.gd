extends SceneTree

const REQUIRED_ROOMS := [
    "res://assets/rooms/R1.glb",
    "res://assets/rooms/R7.glb",
    "res://assets/rooms/R8.glb"
]

var failures: Array[String] = []

func _initialize() -> void:
    call_deferred("_run")

func _check(name: String, condition: bool) -> void:
    if not condition:
        failures.append(name)

func _v3(value: Array) -> Vector3:
    return Vector3(float(value[0]), float(value[1]), float(value[2]))

func _settle(frames: int = 3) -> void:
    for _i in range(frames):
        await process_frame

func _run() -> void:
    var missing: Array[String] = []
    for path in REQUIRED_ROOMS:
        if not ResourceLoader.exists(path):
            missing.append(path)
    if not missing.is_empty():
        print("OPENAZRAEL_KG001_V137 " + JSON.stringify({
            "schema":"openazrael.kg001.trigger_event_runtime",
            "version":137,
            "status":"BLOCKED_MISSING_ASSETS",
            "missing":missing
        }))
        quit(2)
        return

    var events = root.get_node_or_null("LegacyEvents")
    var state = root.get_node_or_null("DemoState")
    if events == null or state == null:
        print("OPENAZRAEL_KG001_V137 " + JSON.stringify({
            "version":137,
            "status":"FAIL",
            "error":"required autoload missing"
        }))
        quit(1)
        return

    events.set_capture_only(true)
    state.reset_all()

    var packed = load("res://main.tscn")
    if packed == null:
        print("OPENAZRAEL_KG001_V137 " + JSON.stringify({
            "version":137,
            "status":"FAIL",
            "error":"cannot load main.tscn"
        }))
        quit(1)
        return

    var scene = packed.instantiate()
    root.add_child(scene)
    await _settle()

    var manager = scene.get_node("RoomManager")
    var player = scene.get_node("Player")

    # Validate the complete classification census at runtime too.
    var evidence: Dictionary = manager.evidence
    var ir: Dictionary = manager.trigger_event_ir
    var total_evidence := 0
    var total_ir := 0
    for room_id in ["R1", "R7", "R8"]:
        var evidence_names := {}
        var ir_names := {}
        for row in evidence["rooms"][room_id]["triggers"]:
            evidence_names[String(row["name"])] = true
            total_evidence += 1
        for row in ir["rooms"][room_id]:
            ir_names[String(row["trigger"])] = true
            total_ir += 1
        _check(room_id + "_trigger_classification_exact", evidence_names.keys().all(func(n): return ir_names.has(n)) and ir_names.keys().all(func(n): return evidence_names.has(n)))

    _check("trigger_count_29", total_evidence == 29 and total_ir == 29)

    # R7/zxactghost: seed outside state first, then cross the real authored
    # boundary. This deliberately uses the same production _process dispatcher.
    manager.transition_cooldown = 999.0
    manager.load_room("R7", false)
    await _settle(2)

    var ghost: Dictionary = manager.call("_trigger_record", "R7", "zxactghost")
    _check("R7_zxactghost_record", not ghost.is_empty())
    var niamh_body = manager.call("_find_node", "nibody")
    _check("R7_niamh_body_exists", niamh_body != null)
    if niamh_body != null:
        # R7_NIAMH_ACTIVATE has no hide/show opcode. The production source
        # contract preserves the authored visible body before animation.
        _check("R7_niamh_source_visible_before_activation", niamh_body.visible)

    if not ghost.is_empty():
        var mn := _v3(ghost["bounds"][0])
        var center := _v3(ghost["centroid"])
        player.global_position = Vector3(mn.x - 40.0, center.y, mn.z - 40.0)
        await _settle(2)
        _check("R7_ghost_outside_seeded", manager._diagnostic_inside.has("zxactghost") and not bool(manager._diagnostic_inside["zxactghost"]))

        player.global_position = center
        await _settle(3)

    _check("R7_niamh_activation_flag", state.flag("R7NiamhActivated"))
    _check("R7_niamh_AZ_state", state.puzzle_node("R7NiamhAZ"))
    if niamh_body != null:
        _check("R7_niamh_visible_after_activation", niamh_body.visible)

    var first_status: Dictionary = manager.character_animation_status("Niamh")
    var animation_status := String(first_status.get("status", ""))
    _check("R7_niamh_animation_request_observed", animation_status in ["PLAYING_SOURCE_CLIP", "HOLD_SOURCE_CLIP_MISSING"])
    if animation_status == "PLAYING_SOURCE_CLIP":
        _check("R7_niamh_source_model_bound", String(first_status.get("model", "")) == "res://assets/characters/Niamh/Niamh.glb")
        _check("R7_niamh_source_clip_bound", String(first_status.get("source", "")) == "res://assets/characters/Niamh/NOLOOP1.tres")
        _check("R7_niamh_rest_queued", String(first_status.get("next_family", "")) == "REST")
        var source_player = manager.get_node_or_null(String(first_status.get("animation_player", ""))) as AnimationPlayer
        var source_root = source_player.get_parent() if source_player != null else null
        _check("R7_niamh_source_hierarchy_instantiated", source_root != null)
        _check("R7_niamh_source_player_exists", source_player != null)
        if source_player != null:
            _check("R7_niamh_noloop1_loaded", source_player.has_animation(&"NOLOOP1"))
            _check("R7_niamh_rest_loaded", source_player.has_animation(&"REST"))
            var source_clip := source_player.get_animation(&"NOLOOP1")
            _check("R7_niamh_noloop1_has_tracks", source_clip != null and source_clip.get_track_count() > 0)
            if source_clip != null:
                var bad_paths: Array[String] = []
                for track_index in source_clip.get_track_count():
                    var node_path := source_clip.track_get_path(track_index)
                    var animation_root = source_player.get_node_or_null(source_player.root_node)
                    if animation_root == null or animation_root.get_node_or_null(node_path.get_concatenated_names()) == null:
                        bad_paths.append(String(node_path))
                _check("R7_niamh_track_paths_resolve", bad_paths.is_empty())

    # One-shot rule: exit and re-enter must not generate a second event graph.
    var flags_before: Dictionary = state.flags.duplicate(true)
    if not ghost.is_empty():
        var mn2 := _v3(ghost["bounds"][0])
        var center2 := _v3(ghost["centroid"])
        player.global_position = Vector3(mn2.x - 40.0, center2.y, mn2.z - 40.0)
        await _settle(2)
        player.global_position = center2
        await _settle(3)
    _check("R7_niamh_one_shot_flag_stable", state.flag("R7NiamhActivated") and state.flags == flags_before)

    var base_status := "PASS" if failures.is_empty() else "FAIL"
    var status := base_status
    var exit_code := 0 if failures.is_empty() else 1
    if failures.is_empty() and animation_status != "PLAYING_SOURCE_CLIP":
        status = "BLOCKED_SOURCE_ANIMATION"
        exit_code = 2

    print("OPENAZRAEL_KG001_V137 " + JSON.stringify({
        "schema":"openazrael.kg001.trigger_event_runtime",
        "version":137,
        "status":status,
        "trigger_count":total_evidence,
        "niamh_animation":first_status,
        "failures":failures,
        "policy":"PASS requires the source-derived NIAMH.XAF hierarchy with NOLOOP1 then REST; HOLD never substitutes synthetic motion."
    }))
    events.set_capture_only(false)
    quit(exit_code)
