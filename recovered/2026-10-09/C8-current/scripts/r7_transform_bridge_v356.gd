extends Node
# Experimental deterministic scheduler/executor bridge. Source semantics are not yet fidelity verified.
const Scheduler = preload("res://scripts/r7_source_action_scheduler_v354.gd")
const Executor = preload("res://scripts/r7_transform_executor_v355.gd")
const Selector = preload("res://scripts/r7_source_action_selector_v359.gd")
const SnapshotValidator = preload("res://scripts/r7_snapshot_validator_v367.gd")
const SOURCE_AXIS_CONTRACT := "res://data/tests/well_source_axis_contract_v361.json"
const EXE_SHA := "381e4f5c61e4bb8c27f06b1944e6673bbebc39ca219cc08fb9f948da2ca37c00"
const WORLD_SHA := "f055948e302fa2f6ba364f7ebd3b4bc45f20ef4445af4946c63e4e313a084ae9"
const PERSIST_KEY := "R7SourceTransformSnapshotV364"
var scheduler: Node
var executor: Node
var applied_count := 0
func _ready() -> void:
    scheduler = Scheduler.new()
    executor = Executor.new()
    add_child(scheduler)
    add_child(executor)
    scheduler.action_step.connect(_on_action_step)
func bind_room(room: Node) -> bool:
    return executor.bind_room(room)
func _on_action_step(action: Dictionary) -> void:
    if executor.apply_step(action):
        applied_count += 1
func queue_action(target_id: int, opcode: int, axis: int, amount: float, steps: int) -> bool:
    return scheduler.enqueue(target_id, opcode, axis, amount, steps)
# These are source-engine vector components, NOT an established Godot
# coordinate-conversion / pivot / rotation-sign parity contract.
func source_axis_component(opcode: int, code: int) -> int:
    if code < 0 or code > 2 or not opcode in [0x17, 0x18]:
        return -1
    if not FileAccess.file_exists(SOURCE_AXIS_CONTRACT):
        return -1
    var contract = JSON.parse_string(FileAccess.get_file_as_string(SOURCE_AXIS_CONTRACT))
    if not contract is Dictionary:
        return -1
    if String(contract.get("schema", "")) != "openazrael.c8.source_axis_contract.v361":
        return -1
    if contract.get("exe_sha256") != EXE_SHA or contract.get("world_sha256") != WORLD_SHA:
        return -1
    if bool(contract.get("production_motion_allowed", true)):
        return -1
    var axes = contract.get("axis_to_source_vector_component")
    if not axes is Dictionary:
        return -1
    var row = axes.get(str(opcode))
    if not row is Dictionary:
        return -1
    var component := int(row.get(str(code), -1))
    return component if component in [0, 1, 2] else -1

# Isolated experimental replay only. Production interaction paths do NOT invoke
# this until original trigger branch, cadence and Godot-space conversion pass.
func queue_experimental_source_step(step: int) -> bool:
    var actions: Array[Dictionary] = Selector.source_step_actions(step)
    if actions.size() != 2:
        return false
    var prepared: Array[Dictionary] = []
    for action in actions:
        var target_id := int(action.get("target_id", -1))
        var opcode := int(action.get("opcode", -1))
        var component := source_axis_component(opcode, int(action.get("axis_code", -1)))
        var steps := int(action.get("steps", -1))
        if not executor.nodes.has(target_id) or component < 0 or steps <= 0:
            return false
        prepared.append({
            "target_id": target_id, "opcode": opcode, "axis": component,
            "amount": float(action.get("operand", 0.0)), "steps": steps
        })
    for action in prepared:
        if not scheduler.enqueue(int(action["target_id"]), int(action["opcode"]),
                int(action["axis"]), float(action["amount"]), int(action["steps"])):
            return false
    persist_to_demo_state()
    return true

func tick() -> void:
    scheduler.tick()
    persist_to_demo_state()
func flush() -> void:
    scheduler.flush()
    persist_to_demo_state()
func snapshot() -> Dictionary:
    return {"version":1,"scheduler":scheduler.snapshot(),"executor":executor.snapshot(),"applied_count":applied_count}
func restore_snapshot(payload: Dictionary) -> bool:
    if not SnapshotValidator.valid(payload):
        return false
    if not payload.get("scheduler") is Dictionary or not payload.get("executor") is Dictionary:
        return false
    # Restore executor first, then the queue. Both payloads are validated by their owners.
    var old = snapshot()
    if not executor.replay_snapshot(payload["executor"]):
        return false
    if not scheduler.restore_snapshot(payload["scheduler"]):
        executor.replay_snapshot(old["executor"])
        return false
    applied_count = int(payload.get("applied_count",0))
    persist_to_demo_state()
    return true

# Only experimental motion writes this key; passive R7 loading leaves legacy
# gameplay saves unchanged. This key is internal, NOT original FLAGLIST state.
func persist_to_demo_state() -> bool:
    var state = get_node_or_null("/root/DemoState")
    if state == null:
        return false
    state.call("set_value", PERSIST_KEY, snapshot())
    return true

func restore_from_demo_state() -> bool:
    var state = get_node_or_null("/root/DemoState")
    if state == null:
        return false
    var saved = state.call("value", PERSIST_KEY, null)
    if saved == null:
        return true
    return saved is Dictionary and restore_snapshot(saved)
