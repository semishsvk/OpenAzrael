extends SceneTree
# Source plaque order, interactive cursors and logical samples; physical fidelity HOLD.
const Cursors = preload("res://scripts/legacy_cursor_catalog_v143.gd")
var failures: Array[String] = []
var checks := 0
func check(name: String, condition: bool) -> void:
    checks += 1
    if not condition:
        failures.append(name)
func _find(node: Node, wanted: String) -> Node:
    if String(node.name) == wanted:
        return node
    for child in node.get_children():
        var found := _find(child,wanted)
        if found != null:
            return found
    return null
func _settle() -> void:
    for i in range(4):
        await process_frame
func _initialize() -> void:
    call_deferred("_run")
func _run() -> void:
    var state = root.get_node_or_null("DemoState")
    var events = root.get_node_or_null("LegacyEvents")
    check("state_exists",state != null)
    check("events_exists",events != null)
    if state == null or events == null:
        _finish(null)
        return
    events.set_capture_only(true)
    events.clear_capture()
    state.reset_all()
    var scene = load("res://main.tscn").instantiate()
    root.add_child(scene)
    await _settle()
    var manager = scene.get_node_or_null("RoomManager")
    check("manager_exists",manager != null)
    if manager == null:
        _finish(scene)
        return
    manager.load_room("R7",false)
    await _settle()
    events.clear_capture()
    var lever = _find(manager.current_room,"Interact_well_lev02")
    var wheel = _find(manager.current_room,"Interact_well_weel3")
    var bridge = _find(manager.current_room,"R7TransformBridge")
    check("right_lever_area",lever != null)
    check("lower_right_wheel_area",wheel != null)
    check("passive_bridge_exists",bridge != null)
    if lever == null or wheel == null:
        _finish(scene)
        return
    check("push_source_cursor_art",Cursors.load_texture("PUSH") != null)
    check("push_cursor_supported",Cursors.normalize_id("PUSH")=="PUSH")
    check("initial_pull_cursor",lever.interaction_cursor_id()=="PULL")
    check("initial_wheel_rot_cursor",wheel.interaction_cursor_id()=="ROT")
    check("initial_puzzle_unsolved",not state.flag("R8BathDrain"))
    lever.interact()
    check("first_lever_step1",int(state.value("R7SwitchStep",-1))==1)
    check("first_pull_audio",events.captured_audio()==["981PULL.WAV"])
    check("still_unsolved",not state.flag("R8BathDrain"))
    check("wheel_expected_cursor",wheel.interaction_cursor_id()=="ROT")
    wheel.interact()
    check("second_wheel_step2",int(state.value("R7SwitchStep",-1))==2)
    check("step2_animated_audio",events.captured_audio()==["981PULL.WAV","977TURN.WAV"])
    check("final_push_cursor",lever.interaction_cursor_id()=="PUSH")
    lever.interact()
    check("third_lever_step3",int(state.value("R7SwitchStep",-1))==3)
    check("drain_flag_set",state.flag("R8BathDrain"))
    check("three_action_audio_exact",events.captured_audio()==["981PULL.WAV","977TURN.WAV","S152V2.WAV","982PUSH.WAV","S16.WAV"])
    check("solved_lever_cant",lever.interaction_cursor_id()=="CANT")
    check("solved_wheel_cant",wheel.interaction_cursor_id()=="CANT")
    var after_solved_audio = events.captured_audio().duplicate()
    lever.interact()
    check("solved_repeat_silent",events.captured_audio()==after_solved_audio)
    check("passive_no_motion",bridge != null and bridge.applied_count==0 and bridge.scheduler.pending.is_empty())
    state.reset_all()
    events.clear_capture()
    wheel.interact()
    check("wrong_first_action_resets",int(state.value("R7SwitchStep",-1))==0)
    check("wrong_action_silent",events.captured_audio().is_empty())
    check("wrong_action_does_not_drain",not state.flag("R8BathDrain"))
    check("wrong_action_restores_pull_cursor",lever.interaction_cursor_id()=="PULL")
    state.reset_all()
    events.set_capture_only(false)
    _finish(scene)
func _finish(scene: Node) -> void:
    if scene != null:
        scene.queue_free()
    await _settle()
    var result = {"schema":"openazrael.c8.r7_plaque_gameplay.v368",
        "status":"PASS" if failures.is_empty() else "FAIL",
        "checks":checks,"failed":failures,
        "original_audio_physical_timing":"HOLD",
        "motion_in_production":false,
        "scope":"source-plaque PULL->TURN->PUSH logical audio and cursor, plus wrong first action"}
    print("OPENAZRAEL_C8_PLAQUE_V368 " + JSON.stringify(result))
    quit(0 if failures.is_empty() else 1)