extends RefCounted
# Experimental source-state interpreter for R7 branches 8/16.
# Only WORLD opcode 0x04 writes are executed; 0x01 is explicitly held.
const Selector = preload("res://scripts/r7_condition_source_selector_v363.gd")
const SOURCE_ARRAY_LEN := 101
var values: PackedInt32Array = PackedInt32Array()
var history: Array[Dictionary] = []
func _init() -> void:
    values.resize(SOURCE_ARRAY_LEN)
    values.fill(0)
func value(index: int) -> int:
    if index < 0 or index >= SOURCE_ARRAY_LEN:
        return -1
    return values[index]
func set_value(index: int, new_value: int) -> bool:
    if index < 0 or index >= SOURCE_ARRAY_LEN or new_value < 0 or new_value > 65535:
        return false
    values[index] = new_value
    return true
func execute_branch(node: int) -> Dictionary:
    if not node in [8,16]:
        return {"status":"REJECTED_UNKNOWN_NODE"}
    var source_index := 44 if node == 8 else 46
    var result: Dictionary = Selector.inspect_branch(node,value(source_index))
    if result.get("status") != "SOURCE_BRANCH_SELECTED_GAMEPLAY_FIDELITY_HOLD":
        return result
    var actions: Array = result["actions"]
    var updated := values.duplicate()
    var events: Array[Dictionary] = []
    var opaque_count := 0
    for a in actions:
        if not a is Dictionary:
            return {"status":"REJECTED_MALFORMED_ACTION"}
        var kind := String(a.get("kind",""))
        var event: Dictionary = {"kind":kind,"opcode":int(a.get("opcode",-1)),"ordinal":int(a.get("ordinal",-1))}
        match kind:
            "state_write":
                var index := int(a.get("source_state_index",-1))
                var source_value := int(a.get("source_state_value",-1))
                if index < 0 or index >= SOURCE_ARRAY_LEN or source_value < 0 or source_value > 65535:
                    return {"status":"REJECTED_INVALID_STATE_WRITE"}
                updated[index] = source_value
                event["source_state_index"] = index
                event["source_state_value"] = source_value
            "rotation","translation":
                event["target_id"] = int(a.get("target_id",-1))
                event["operand"] = float(a.get("operand",0))
            "sound":
                event["source_audio"] = String(a.get("sound_file",""))
            "opaque_state_action":
                opaque_count += 1
                event["unverified"] = true
            _:
                return {"status":"REJECTED_UNKNOWN_ACTION"}
        events.append(event)
    values = updated
    var trace = {"status":"PARTIAL_SOURCE_STATE_REPLAY_OPCODE01_HOLD","node":node,
        "slot":int(result["slot"]),"condition_index":source_index,
        "condition_before":int(result["source_condition_value"]),
        "condition_after":value(source_index),"events":events,
        "opaque_actions":opaque_count,"audio_played":false,"physical_motion_applied":false}
    history.append(trace.duplicate(true))
    return trace