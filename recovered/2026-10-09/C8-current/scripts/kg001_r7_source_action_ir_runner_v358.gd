extends SceneTree
const DATA := "res://data/runtime_generated/well_source_actions_v358.json"
var failures: Array[String] = []
var checks := 0
func check(name: String, ok: bool) -> void:
    checks += 1
    if not ok: failures.append(name)
func _initialize() -> void: call_deferred("run_test")
func run_test() -> void:
    var data = JSON.parse_string(FileAccess.get_file_as_string(DATA))
    check("json",data is Dictionary)
    if not data is Dictionary:
        finish()
        return
    check("schema",data.get("schema") == "openazrael.c8.well_actions.v358")
    var rows: Array = data.get("records",[])
    check("count",rows.size() == 24)
    var nodes: Dictionary = {}
    for row in rows:
        var n := int(row["node"])
        if not nodes.has(n): nodes[n] = []
        nodes[n].append(row)
    check("ten_nodes",nodes.size() == 10)
    check("lever_four",nodes[16].size() == 4)
    check("wheel_pair",nodes[13].size() == 2 and nodes[14].size() == 2)
    var rotation_count := 0
    var translation_count := 0
    for row in rows:
        if int(row["opcode"]) == 23: rotation_count += 1
        if int(row["opcode"]) == 24: translation_count += 1
    check("rotation_count",rotation_count == 16)
    check("translation_count",translation_count == 8)
    finish()
func finish() -> void:
    var out = {"status":"PASS" if failures.is_empty() else "FAIL","checks":checks,"failed":failures,"scope":"source action IR load; no gameplay action activation or fidelity assertion"}
    print("OPENAZRAEL_C8_ACTION_IR_V358 " + JSON.stringify(out))
    quit(0 if failures.is_empty() else 1)