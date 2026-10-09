extends RefCounted
# Select COMPLETE source-ordered Well Room action chains using original numeric
# state-array values, not reconstructed R7SwitchStep. No production activation.
const DATA := "res://data/runtime_generated/well_interaction_source_v363.json"
const SHA := "f055948e302fa2f6ba364f7ebd3b4bc45f20ef4445af4946c63e4e313a084ae9"
const NODE_CONDITIONS := {8: 44, 16: 46}
static func inspect_branch(node: int, source_state_value: int) -> Dictionary:
    if not NODE_CONDITIONS.has(node):
        return {"status":"REJECTED_UNKNOWN_SOURCE_NODE"}
    if not FileAccess.file_exists(DATA):
        return {"status":"BLOCKED_SOURCE_IR_MISSING"}
    var ir = JSON.parse_string(FileAccess.get_file_as_string(DATA))
    if not ir is Dictionary or ir.get("schema") != "openazrael.c8.well_interaction_source.v363":
        return {"status":"BLOCKED_SOURCE_SCHEMA"}
    if ir.get("world_sha256") != SHA or not ir.get("groups") is Array:
        return {"status":"BLOCKED_SOURCE_IDENTITY"}
    if ir.get("status") != "SOURCE_ACTION_ORDER_AND_STATE_WRITE_PASS_GAMEPLAY_FIDELITY_HOLD":
        return {"status":"BLOCKED_SOURCE_SEMANTIC_VERSION"}
    var slot := 0 if source_state_value != 0 else 1
    for branch in ir["groups"]:
        if int(branch.get("node",-1)) != node or int(branch.get("slot",-1)) != slot:
            continue
        var condition = branch.get("condition",{})
        if not condition is Dictionary:
            return {"status":"BLOCKED_CONDITION_SCHEMA"}
        if int(condition.get("state_index_candidate",-1)) != int(NODE_CONDITIONS[node]):
            return {"status":"BLOCKED_CONDITION_INDEX"}
        if int(condition.get("opcode",-1)) != (4 if slot == 0 else 10):
            return {"status":"BLOCKED_CONDITION_OPCODE"}
        if String(condition.get("predicate","")) != ("nonzero" if slot == 0 else "zero"):
            return {"status":"BLOCKED_CONDITION_PREDICATE"}
        var actions = branch.get("actions")
        if not actions is Array or actions.size() != (5 if slot == 0 else 7):
            return {"status":"BLOCKED_ACTION_POPULATION"}
        return {
            "status":"SOURCE_BRANCH_SELECTED_GAMEPLAY_FIDELITY_HOLD",
            "source_condition_index":NODE_CONDITIONS[node],
            "source_condition_value":source_state_value,
            "node":node,"slot":slot,"actions":actions.duplicate(true),
            "production_motion_allowed":false
        }
    return {"status":"BLOCKED_SOURCE_BRANCH_ABSENT"}