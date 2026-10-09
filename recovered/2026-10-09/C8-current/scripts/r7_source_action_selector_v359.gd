extends RefCounted
# Source-bound R7 action selector. Slot/node mapping is explicit, axis remains unverified.
const DATA_PATH := "res://data/runtime_generated/well_source_actions_v358.json"
static func load_ir() -> Dictionary:
    if not FileAccess.file_exists(DATA_PATH):
        return {}
    var parsed = JSON.parse_string(FileAccess.get_file_as_string(DATA_PATH))
    if not parsed is Dictionary or String(parsed.get("schema","")) != "openazrael.c8.well_actions.v358":
        return {}
    if String(parsed.get("source_sha256","")) != "f055948e302fa2f6ba364f7ebd3b4bc45f20ef4445af4946c63e4e313a084ae9":
        return {}
    if not parsed.get("records") is Array or parsed["records"].size() != 24:
        return {}
    for row in parsed["records"]:
        if not row is Dictionary or not int(row.get("axis_code", -1)) in [0, 1, 2] or row.has("mode"):
            return {}
    return parsed
static func select_actions(node_id: int, slot: int) -> Array[Dictionary]:
    var data := load_ir()
    var result: Array[Dictionary] = []
    if data.is_empty():
        return result
    for row in data["records"]:
        if int(row.get("node",-1)) == node_id and int(row.get("slot",-1)) == slot:
            result.append(row.duplicate(true))
    return result
static func source_step_actions(step: int) -> Array[Dictionary]:
    match step:
        0:
            return select_actions(16, 1)
        1:
            return select_actions(13, 0)
        2:
            return select_actions(16, 0)
    return []