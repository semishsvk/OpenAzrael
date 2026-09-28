extends RefCounted
class_name PPPVEvidenceBus

const SCHEMA := "remaster.runtime_evidence"
const VERSION := 1

var _events: Array[Dictionary] = []
var _next_id := 1

func clear() -> void:
    _events.clear()
    _next_id = 1

func record(kind: String, payload: Dictionary = {}, room: String = "") -> Dictionary:
    var event := {
        "event_id": "ev_%06d" % _next_id,
        "frame": Engine.get_physics_frames(),
        "kind": kind,
        "payload": payload.duplicate(true)
    }
    if not room.is_empty():
        event["room"] = room
    _events.append(event)
    _next_id += 1
    return event

func record_player_action(
    action_id: String,
    execution_mode: String,
    details: Dictionary = {}
) -> Dictionary:
    var payload := details.duplicate(true)
    payload["action_id"] = action_id
    payload["execution_mode"] = execution_mode
    return record("player_action", payload)

func record_interaction_probe(
    target: String,
    reachable: bool,
    actual_target: String = ""
) -> Dictionary:
    return record("interaction_probe", {
        "target": target,
        "reachable": reachable,
        "actual_target": actual_target
    })

func record_audio(asset: String, details: Dictionary = {}) -> Dictionary:
    var payload := details.duplicate(true)
    payload["asset"] = asset
    return record("audio", payload)

func record_demo_action_step(step: String) -> Dictionary:
    return record("demo_action_step", {"step": step})

func events() -> Array[Dictionary]:
    return _events.duplicate(true)

func bundle() -> Dictionary:
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "events": events()
    }

func write_json(path: String) -> bool:
    var file := FileAccess.open(path, FileAccess.WRITE)
    if file == null:
        return false
    file.store_string(JSON.stringify(bundle(), "  "))
    file.store_string("\n")
    file.close()
    return true
