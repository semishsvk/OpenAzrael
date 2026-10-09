extends SceneTree
const Validator = preload("res://scripts/r7_snapshot_validator_v367.gd")
var failures: Array[String] = []
var checks := 0
func check(label: String, condition: bool) -> void:
    checks += 1
    if not condition:
        failures.append(label)
func _initialize() -> void:
    call_deferred("_run")
func _invalid_save(state: Node, payload: Array, bad_value, label: String) -> void:
    var bad: Array = payload.duplicate(true)
    var found := false
    for pair in bad[4]:
        if pair[0] == Validator.KEY:
            pair[1] = bad_value
            found = true
    check(label + "_found", found)
    var before: String = state.canonical_state_hash()
    check(label + "_rejected", not state.restore_canonical_state_payload(bad))
    check(label + "_atomic", state.canonical_state_hash() == before)
func _run() -> void:
    var state: Node = root.get_node("DemoState")
    state.reset_all()
    var action = {"target_id":1145,"opcode":0x18,"axis":0,"amount":-1.0,"remaining":4,"total":5}
    var snap: Dictionary = {
        "version":1,
        "scheduler":{"version":1,"tick_index":1,"pending":[action.duplicate(true)]},
        "executor":{"version":1,"applied":[action.duplicate(true)]},
        "applied_count":1
    }
    check("valid_snapshot",Validator.valid(snap))
    state.set_value(Validator.KEY,snap)
    state.set_flag("R1Door1Open")
    state.acquire("well_key")
    var payload: Array = state.canonical_state_payload().duplicate(true)
    var good_hash: String = state.canonical_state_hash()
    state.reset_all()
    check("valid_restore",state.restore_canonical_state_payload(payload))
    check("valid_restore_hash",state.canonical_state_hash() == good_hash)
    check("valid_restore_inventory",state.has("well_key"))
    check("valid_restore_flag",state.flag("R1Door1Open"))
    _invalid_save(state,payload,{"version":1},"missing_nested")
    var bad_version = snap.duplicate(true)
    bad_version["version"] = 2
    _invalid_save(state,payload,bad_version,"bad_version")
    var bad_opcode = snap.duplicate(true)
    bad_opcode["scheduler"]["pending"][0]["opcode"] = 99
    _invalid_save(state,payload,bad_opcode,"bad_opcode")
    var bad_target = snap.duplicate(true)
    bad_target["executor"]["applied"][0]["target_id"] = 9999
    _invalid_save(state,payload,bad_target,"bad_target")
    var bad_axis = snap.duplicate(true)
    bad_axis["scheduler"]["pending"][0]["axis"] = 3
    _invalid_save(state,payload,bad_axis,"bad_axis")
    var bad_remaining = snap.duplicate(true)
    bad_remaining["scheduler"]["pending"][0]["remaining"] = 0
    _invalid_save(state,payload,bad_remaining,"bad_remaining")
    var bad_amount = snap.duplicate(true)
    bad_amount["executor"]["applied"][0]["amount"] = "invalid"
    _invalid_save(state,payload,bad_amount,"bad_amount")
    var bad_count = snap.duplicate(true)
    bad_count["applied_count"] = 2
    _invalid_save(state,payload,bad_count,"bad_count")
    var bad_tick = snap.duplicate(true)
    bad_tick["scheduler"]["tick_index"] = -1
    _invalid_save(state,payload,bad_tick,"bad_tick")
    _invalid_save(state,payload,null,"null_snapshot")
    check("still_old_hash",state.canonical_state_hash() == good_hash)
    check("still_old_inventory",state.has("well_key"))
    check("still_old_flag",state.flag("R1Door1Open"))
    state.reset_all()
    var legacy_payload: Array = state.canonical_state_payload().duplicate(true)
    check("legacy_without_key_accepted",state.restore_canonical_state_payload(legacy_payload))
    check("legacy_no_spurious_state",state.value(Validator.KEY,null) == null)
    var out = {"schema":"openazrael.c8.r7_save_validation.v367",
        "status":"PASS" if failures.is_empty() else "FAIL",
        "checks":checks,"failed":failures,
        "scope":"DemoState canonical validation and atomic rejection of malformed experimental R7 transform snapshots"}
    print("OPENAZRAEL_C8_SNAPSHOT_GUARD_V367 " + JSON.stringify(out))
    quit(0 if failures.is_empty() else 1)