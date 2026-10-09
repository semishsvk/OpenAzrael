extends RefCounted
# R7-only serialized experimental snapshot contract.
# No assertion about original WORLD save format or visual fidelity.
const KEY := "R7SourceTransformSnapshotV364"
const TARGET_IDS := [98,99,100,101,222,223,224,225,1145,1148]
const MAX_ACTIONS := 10000
const MAX_PENDING := 64
static func _whole(value, low: int, high: int) -> bool:
    if typeof(value) != TYPE_INT and typeof(value) != TYPE_FLOAT:
        return false
    var f := float(value)
    return not is_nan(f) and not is_inf(f) and f >= low and f <= high and f == floor(f)
static func _valid_action(raw, pending: bool) -> bool:
    if not raw is Dictionary:
        return false
    if not _whole(raw.get("target_id",null),0,2000):
        return false
    if not int(raw["target_id"]) in TARGET_IDS:
        return false
    if not _whole(raw.get("opcode",null),0,255) or not int(raw["opcode"]) in [0x17,0x18]:
        return false
    if not _whole(raw.get("axis",null),0,2):
        return false
    var number = raw.get("amount",null)
    if typeof(number) not in [TYPE_INT, TYPE_FLOAT]:
        return false
    var amount := float(number)
    if is_nan(amount) or is_inf(amount) or abs(amount)>10000.0:
        return false
    if not _whole(raw.get("total",null),1,1000):
        return false
    if not _whole(raw.get("remaining",null),0,1000):
        return false
    if int(raw["remaining"]) > int(raw["total"]):
        return false
    return not pending or int(raw["remaining"]) > 0
static func valid(snapshot) -> bool:
    if not snapshot is Dictionary or not _whole(snapshot.get("version",null),1,1):
        return false
    var scheduler = snapshot.get("scheduler")
    var executor = snapshot.get("executor")
    if not scheduler is Dictionary or not executor is Dictionary:
        return false
    if not _whole(scheduler.get("version",null),1,1) or not _whole(executor.get("version",null),1,1):
        return false
    if not _whole(scheduler.get("tick_index",null),0,10000000):
        return false
    if not _whole(snapshot.get("applied_count",null),0,MAX_ACTIONS):
        return false
    var pending = scheduler.get("pending")
    var applied = executor.get("applied")
    if not pending is Array or not applied is Array:
        return false
    if pending.size() > MAX_PENDING or applied.size() > MAX_ACTIONS:
        return false
    if int(snapshot["applied_count"]) != applied.size():
        return false
    for a in pending:
        if not _valid_action(a,true):
            return false
    for a in applied:
        if not _valid_action(a,false):
            return false
    return true