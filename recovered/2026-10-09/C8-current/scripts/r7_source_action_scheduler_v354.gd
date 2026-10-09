extends Node
# Deterministic source-action scheduler. No scene transforms until fidelity binding is verified.
signal action_step(action: Dictionary)
signal action_finished(action: Dictionary)
var pending: Array[Dictionary] = []
var tick_index := 0
func enqueue(target_id: int, opcode: int, axis: int, amount: float, steps: int) -> bool:
    if steps <= 0 or not opcode in [0x17, 0x18]:
        return false
    pending.push_front({"target_id":target_id,"opcode":opcode,"axis":axis,"amount":amount,"remaining":steps,"total":steps})
    return true
func tick() -> void:
    tick_index += 1
    var next_pending: Array[Dictionary] = []
    for item in pending:
        var action := item.duplicate(true)
        action["remaining"] = int(action["remaining"]) - 1
        action_step.emit(action.duplicate(true))
        if int(action["remaining"]) <= 0:
            action_finished.emit(action.duplicate(true))
        else:
            next_pending.append(action)
    pending = next_pending
func flush() -> void:
    while not pending.is_empty():
        tick()
func snapshot() -> Dictionary:
    return {"version":1,"tick_index":tick_index,"pending":pending.duplicate(true)}
func restore_snapshot(payload: Dictionary) -> bool:
    if int(payload.get("version", -1)) != 1 or not payload.get("pending") is Array:
        return false
    var validated: Array[Dictionary] = []
    for raw in payload["pending"]:
        if not raw is Dictionary:
            return false
        var opcode := int(raw.get("opcode", -1))
        var total := int(raw.get("total", -1))
        var remaining := int(raw.get("remaining", -1))
        if not opcode in [0x17, 0x18] or total <= 0 or remaining <= 0 or remaining > total:
            return false
        validated.append(raw.duplicate(true))
    var next_tick := int(payload.get("tick_index", -1))
    if next_tick < 0:
        return false
    tick_index = next_tick
    pending = validated
    return true