extends SceneTree
const Selector = preload("res://scripts/r7_condition_source_selector_v363.gd")
var failures: Array[String] = []
var checks := 0
func check(name: String, good: bool) -> void:
    checks += 1
    if not good:
        failures.append(name)
func _initialize() -> void:
    call_deferred("_run")
func _run() -> void:
    for node in [8,16]:
        var a: Dictionary = Selector.inspect_branch(node,1)
        var b: Dictionary = Selector.inspect_branch(node,0)
        check("nonzero_selected_"+str(node), a["status"] == "SOURCE_BRANCH_SELECTED_GAMEPLAY_FIDELITY_HOLD")
        check("zero_selected_"+str(node), b["status"] == "SOURCE_BRANCH_SELECTED_GAMEPLAY_FIDELITY_HOLD")
        check("correct_slots_"+str(node), int(a["slot"]) == 0 and int(b["slot"]) == 1)
        check("different_lengths_"+str(node), a["actions"].size() == 5 and b["actions"].size() == 7)
        var a_sound: Array[String] = []
        var b_sound: Array[String] = []
        for item in a["actions"]:
            if item.get("kind") == "sound": a_sound.append(String(item["sound_file"]))
        for item in b["actions"]:
            if item.get("kind") == "sound": b_sound.append(String(item["sound_file"]))
        check("push_audio_"+str(node), a_sound == ["982PUSH.WAV"])
        check("pull_audio_"+str(node), b_sound == ["981PULL.WAV"])
        check("production_disabled_"+str(node), a["production_motion_allowed"] == false and b["production_motion_allowed"] == false)
        check("source_condition_index_"+str(node), int(a["source_condition_index"]) == (44 if node == 8 else 46))
    check("unknown_node_rejected",Selector.inspect_branch(999,1)["status"] == "REJECTED_UNKNOWN_SOURCE_NODE")
    var out={"schema":"openazrael.c8.r7_condition_branch.v363",
        "status":"PASS" if failures.is_empty() else "FAIL",
        "checks":checks,"failed":failures,
        "fidelity_status":"HOLD",
        "scope":"original WORLD numerical flag predicate and source action chain, not gameplay flag binding"}
    print("OPENAZRAEL_C8_CONDITION_BRANCH_V363 "+JSON.stringify(out))
    quit(0 if failures.is_empty() else 1)