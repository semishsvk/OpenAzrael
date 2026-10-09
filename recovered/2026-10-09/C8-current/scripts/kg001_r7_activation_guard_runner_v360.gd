extends SceneTree
const Guard = preload("res://scripts/r7_action_activation_guard_v360.gd")
var failures: Array[String] = []
var checks := 0
func check(name: String, ok: bool) -> void:
    checks += 1
    if not ok: failures.append(name)
func _initialize() -> void: call_deferred("run_test")
func run_test() -> void:
    for step in range(3):
        var result = Guard.inspect_step(step)
        check("source_ready_"+str(step),result["status"]=="SOURCE_ACTIONS_READY_FIDELITY_HOLD")
        check("two_actions_"+str(step),result["actions"].size()==2)
        check("not_authorized_"+str(step),not Guard.activation_allowed(step))
    check("invalid_rejected",Guard.inspect_step(99)["status"]=="REJECTED_INVALID_STEP")
    check("invalid_not_authorized",not Guard.activation_allowed(99))
    var out={"status":"PASS" if failures.is_empty() else "FAIL","checks":checks,"failed":failures,"scope":"fail-closed source activation guard; no gameplay motion"}
    print("OPENAZRAEL_C8_ACTIVATION_GUARD_V360 "+JSON.stringify(out))
    quit(0 if failures.is_empty() else 1)