extends SceneTree
const Machine = preload("res://scripts/r7_source_state_machine_v365.gd")
var errors: Array[String] = []
var checks := 0
func check(name: String, ok: bool) -> void:
    checks += 1
    if not ok:
        errors.append(name)
func _initialize() -> void:
    call_deferred("_run")
func _sounds(trace: Dictionary) -> Array[String]:
    var sounds: Array[String] = []
    for event in trace.get("events",[]):
        if event.get("kind") == "sound":
            sounds.append(String(event.get("source_audio","")))
    return sounds
func _run() -> void:
    var source = Machine.new()
    check("initial_indices_zero",source.value(44)==0 and source.value(46)==0)
    check("101_bounds_rejected",not source.set_value(101,1))
    check("negative_rejected",not source.set_value(-1,1))
    check("overflow_rejected",not source.set_value(46,65536))
    check("unknown_node_rejected",source.execute_branch(99)["status"]=="REJECTED_UNKNOWN_NODE")
    check("rejected_no_mutation",source.history.is_empty())
    check("seed_other_flags",source.set_value(42,1) and source.set_value(43,1))
    var lever_first: Dictionary = source.execute_branch(16)
    check("lever_first_slot1",int(lever_first.get("slot",-1))==1)
    check("lever_first_pull",_sounds(lever_first)==["981PULL.WAV"])
    check("lever_first_state46_one",source.value(46)==1)
    check("lever_sideflags_reset",source.value(42)==0 and source.value(43)==0)
    check("lever_first_7_events",lever_first["events"].size()==7)
    check("lever_first_opaque_hold",int(lever_first["opaque_actions"])==1)
    check("lever_first_no_playback",not bool(lever_first["audio_played"]))
    var lever_second: Dictionary = source.execute_branch(16)
    check("lever_second_slot0",int(lever_second.get("slot",-1))==0)
    check("lever_second_push",_sounds(lever_second)==["982PUSH.WAV"])
    check("lever_second_state46_zero",source.value(46)==0)
    check("lever_second_5_events",lever_second["events"].size()==5)
    var other_first: Dictionary = source.execute_branch(8)
    check("other_first_slot1",int(other_first.get("slot",-1))==1)
    check("other_first_pull",_sounds(other_first)==["981PULL.WAV"])
    check("other_state44_one",source.value(44)==1)
    var other_second: Dictionary = source.execute_branch(8)
    check("other_second_slot0",int(other_second.get("slot",-1))==0)
    check("other_second_push",_sounds(other_second)==["982PUSH.WAV"])
    check("other_state44_zero",source.value(44)==0)
    check("other_independent_46",source.value(46)==0)
    check("four_source_traces",source.history.size()==4)
    var expected: Array = ["translation","rotation","state_write","opaque_state_action","state_write","state_write","sound"]
    var observed: Array = []
    for event in lever_first["events"]:
        observed.append(event["kind"])
    check("source_order_preserved",observed==expected)
    check("no_scene_animation",not bool(lever_second["physical_motion_applied"]))
    var out = {"schema":"openazrael.c8.well_source_state_model.v365",
        "status":"PASS" if errors.is_empty() else "FAIL",
        "checks":checks,"failed":errors,"source_state_array_length":101,
        "scope":"isolated original opcode 04 and conditional 04/0A semantics; opcode 01, trigger identity, motion and physical audio HOLD"}
    print("OPENAZRAEL_C8_SOURCE_STATE_V365 " + JSON.stringify(out))
    quit(0 if errors.is_empty() else 1)