extends SceneTree
# First authentic R7 visit automatically enters Niamh's authored zxactghost,
# with no keypress, M toggle, object click or explicit conversation request.
# Test source one-shot, return to R7, and save/load without a second activation.
var failed: Array[String] = []
var checks := 0
var ghost_dispatches := 0
var conversations := 0
var source_animations := 0

func check(label: String, condition: bool) -> void:
    checks += 1
    if not condition:
        failed.append(label)

func _initialize() -> void:
    call_deferred("_run")

func settle(count: int = 4) -> void:
    for i in count:
        await process_frame

func _observe(e: Dictionary) -> void:
    var name := String(e.get("kind", ""))
    var data = e.get("data", {})
    if not data is Dictionary:
        return
    if name == "trigger_event_dispatch" and String(data.get("trigger","")) == "zxactghost" and String(data.get("status","")) == "DISPATCHED":
        ghost_dispatches += 1
    if name == "conversation_request" and String(data.get("character","")) == "Niamh" and String(data.get("status","")) == "SOURCE_CONVERSATION_IR_READY":
        conversations += 1
    if name == "character_animation_request" and String(data.get("character","")) == "Niamh" and String(data.get("family","")) == "NOLOOP1":
        source_animations += 1

func _run() -> void:
    var state = root.get_node_or_null("DemoState")
    var diagnostics = root.get_node_or_null("CandidateDiagnostics")
    var events = root.get_node_or_null("LegacyEvents")
    check("autoload_state", state != null)
    check("autoload_diagnostics", diagnostics != null)
    check("autoload_events", events != null)
    if state == null or diagnostics == null or events == null:
        finish(null)
        return
    diagnostics.event_recorded.connect(_observe)
    events.set_capture_only(true)
    state.reset_all()
    var scene = load("res://main.tscn").instantiate()
    root.add_child(scene)
    await settle()
    var manager = scene.get_node("RoomManager")
    var player = scene.get_node("Player")
    var ui = scene.get_node("ConversationUIV208")
    manager.transition_cooldown = 999.0
    check("entry_portal", manager.load_room_at_portal("R7", "view", false))
    await settle(2)
    check("room_R7", manager.current_room_id == "R7")
    var ghost = manager._trigger_record("R7", "zxactghost")
    check("authored_ghost_volume_exists", not ghost.is_empty())
    check("not_started_by_key_or_click", not state.flag("R7NiamhActivated"))
    check("no_entry_dialog_before_ghost", not bool(ui.active))
    if ghost.is_empty():
        finish(scene)
        return
    var box: Array = ghost["bounds"]
    var center = ghost["centroid"]
    var target := Vector3(float(center[0]), float(center[1]), float(center[2]))
    check("spawn_outside_authored_ghost", not manager._inside_trigger(player.global_position, ghost))
    check("target_inside_authored_ghost", manager._inside_trigger(target, ghost))
    player.global_position = target
    await settle()
    check("auto_ghost_first_crossing", state.flag("R7NiamhActivated"))
    check("auto_original_puzzle_node", state.puzzle_node("R7NiamhAZ"))
    check("one_trigger_dispatch", ghost_dispatches == 1)
    check("one_animation_request", source_animations == 1)
    check("one_conversation_request", conversations == 1)
    check("dialog_auto_open", ui.active)
    var animation = manager.character_animation_status("Niamh")
    check("source_NOLOOP1_bound", String(animation.get("family",""))=="NOLOOP1" and String(animation.get("status",""))=="PLAYING_SOURCE_CLIP")
    check("source_REST_queued", String(animation.get("next_family",""))=="REST")
    var exit_choice: Dictionary = {}
    for row in ui.choices:
        if String(row.get("id","")) == "999":
            exit_choice = row
    check("source_exit_choice_present", not exit_choice.is_empty())
    if not exit_choice.is_empty():
        ui._show_response(exit_choice)
        var key=InputEventKey.new()
        key.keycode=KEY_ENTER
        key.pressed=true
        ui._unhandled_input(key)
        check("dialog_exit_processed", not ui.active and not paused)
        check("NOLOOP2_exit_animation", String(manager.character_animation_status("Niamh").get("family",""))=="NOLOOP2")
    else:
        ui._close()
    var preserved: Array = state.canonical_state_payload().duplicate(true)
    check("first_session_saved_flag", state.flag("R7NiamhActivated"))
    check("return_to_R1", manager.load_room_at_portal("R1", "spaview", false))
    await settle(2)
    check("return_to_R7", manager.load_room_at_portal("R7", "view", false))
    await settle(2)
    player.global_position = target
    await settle(3)
    check("no_second_ghost_dispatch", ghost_dispatches==1)
    check("no_second_conversation", conversations==1)
    check("no_second_animation", source_animations==1)
    check("no_second_dialog_ui", not ui.active)
    check("one_shot_persisted", state.flag("R7NiamhActivated"))
    check("save_leave_to_R1", manager.load_room_at_portal("R1", "spaview", false))
    await settle(2)
    state.reset_all()
    check("canonical_load", state.restore_canonical_state_payload(preserved))
    check("loaded_one_shot_flag", state.flag("R7NiamhActivated"))
    check("loaded_return_to_R7", manager.load_room_at_portal("R7","view",false))
    await settle(2)
    player.global_position = target
    await settle(3)
    check("saved_game_no_reactivation", ghost_dispatches==1 and conversations==1 and source_animations==1 and not ui.active)
    check("saved_game_one_shot_stable", state.flag("R7NiamhActivated"))

    # If a legitimate room load begins already overlapping the authored
    # zxactghost volume, it must not silently miss this one-shot event.
    check("leave_before_initial_overlap_case", manager.load_room_at_portal("R1","spaview",false))
    state.reset_all()
    player.global_position = target
    manager.transition_cooldown = 999.0
    manager.load_room("R7",false)
    await settle(3)
    check("auto_initial_overlap_once", state.flag("R7NiamhActivated"))
    check("auto_initial_overlap_event_increment", ghost_dispatches == 2)
    check("auto_initial_overlap_conversation_increment", conversations == 2)
    check("auto_initial_overlap_animation_increment", source_animations == 2)
    if ui.active:
        ui._close()
    state.reset_all()
    finish(scene)

func finish(scene: Node) -> void:
    paused = false
    if scene != null:
        scene.queue_free()
    await settle(2)
    var result = {"schema":"openazrael.c8.niamh_auto_once.v403",
        "status":"PASS" if failed.is_empty() else "FAIL",
        "checks":checks,"failed":failed,"dispatches":ghost_dispatches,
        "conversation_requests":conversations,"source_animation_requests":source_animations,
        "automatic_source_trigger":"R7/zxactghost",
        "first_entry":"NO_MANUAL_CLICK_OR_M_KEY",
        "return_visit":"NO_REPLAY",
        "save_restore":"ONE_SHOT_PERSISTS",
        "fidelity":"ORIGINAL_VISIBLE_ANIMATION_TIMING_HOLD"}
    print("OPENAZRAEL_NIAMH_AUTO_ONCE_V403 " + JSON.stringify(result))
    quit(0 if failed.is_empty() else 1)