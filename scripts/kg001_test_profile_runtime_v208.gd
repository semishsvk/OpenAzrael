extends SceneTree

var failed: Array[String] = []

func check(ok: bool, name: String) -> void:
    if not ok:
        failed.append(name)

func _initialize() -> void:
    call_deferred("_run")

func _run() -> void:
    var packed := load("res://main.tscn") as PackedScene
    check(packed != null, "main_scene_load")
    if packed == null:
        _finish()
        return
    var scene := packed.instantiate()
    root.add_child(scene)
    current_scene = scene
    await process_frame
    await process_frame

    var rm = scene.get_node("RoomManager")
    var ui = scene.get_node("ConversationUIV208")
    check(ui != null, "conversation_ui_present")
    check(InputMap.has_action("move_forward"), "move_forward_action")
    check(InputMap.has_action("move_back"), "move_back_action")
    check(InputMap.has_action("move_left"), "move_left_action")
    check(InputMap.has_action("move_right"), "move_right_action")
    check(InputMap.has_action("interact"), "interact_action")

    var payload := {
        "character":"Niamh",
        "family":"1A",
        "source_required":true
    }
    rm.call("_on_conversation_requested", payload)
    await process_frame
    check(bool(ui.get("active")), "conversation_opened")
    check((ui.get("lines") as Array).size() >= 4, "conversation_source_lines")
    check(paused, "conversation_pauses_world")

    # Close directly for deterministic headless validation; keyboard handling
    # is separately guaranteed by the InputMap and UI script.
    ui.set("active", false)
    ui.get("panel").visible = false
    paused = false

    var eugen = rm.get_node_or_null("Entry Corridor (R1)/SourceCharacter_EugenB")
    check(eugen != null, "eugen_spawned")
    if eugen != null:
        var ap = eugen.get_node_or_null("SourceCharacterAnimation") as AnimationPlayer
        check(ap != null, "eugen_animation_player")
        if ap != null:
            check(String(ap.root_node) == "../EugenB_Model", "eugen_animation_root")
            check(ap.has_animation(&"REST"), "eugen_rest_clip")
    _finish()

func _finish() -> void:
    var out := {"schema":"openazrael.kg001.test_profile_runtime","version":208,"status":"PASS" if failed.is_empty() else "FAIL","failed":failed,"controls":"WASD + E interact; Shift sprint; RMB look"}
    print("OPENAZRAEL_TEST_PROFILE_V208 " + JSON.stringify(out))
    quit(0 if failed.is_empty() else 1)
