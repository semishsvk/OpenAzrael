extends RefCounted
# C8 bounded source-action activation contract: explicit hold until axis/trigger proof.
const Selector = preload("res://scripts/r7_source_action_selector_v359.gd")
const REQUIRED := {
    0: {"node":16,"slot":1,"count":2},
    1: {"node":13,"slot":0,"count":2},
    2: {"node":16,"slot":0,"count":2}
}
static func inspect_step(step: int) -> Dictionary:
    if not REQUIRED.has(step):
        return {"status":"REJECTED_INVALID_STEP","actions":[]}
    var spec: Dictionary = REQUIRED[step]
    var actions = Selector.select_actions(int(spec["node"]),int(spec["slot"]))
    if actions.size() != int(spec["count"]):
        return {"status":"BLOCKED_SOURCE_ACTIONS","actions":[]}
    for row in actions:
        if int(row.get("steps",-1)) <= 0 or not int(row.get("opcode",-1)) in [23,24] or int(row.get("axis_code",-1)) not in [0,1,2]:
            return {"status":"BLOCKED_INVALID_ACTION","actions":[]}
    return {"status":"SOURCE_ACTIONS_READY_FIDELITY_HOLD","actions":actions,"node":spec["node"],"slot":spec["slot"],"unverified":["godot_coordinate_conversion","transform_composition","trigger_semantics","cadence","audio_sync"]}
static func activation_allowed(step: int) -> bool:
    # Fail closed: a source-bound action record alone does not authorize motion.
    return false