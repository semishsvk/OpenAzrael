extends SceneTree
const Executor = preload("res://scripts/r7_transform_executor_v355.gd")
var failed: Array[String] = []
var checks := 0
func check(name: String, ok: bool) -> void:
    checks += 1
    if not ok: failed.append(name)
func _initialize() -> void: call_deferred("run_test")
func run_test() -> void:
    var scene = load("res://assets/rooms/R7.glb").instantiate()
    root.add_child(scene)
    var executor = Executor.new()
    root.add_child(executor)
    check("bind_all", executor.bind_room(scene))
    check("ten_targets", executor.nodes.size() == 10)
    if executor.nodes.size() == 10:
        var baseline: Transform3D = executor.nodes[1145].transform
        var r = {"target_id":1145,"opcode":0x17,"axis":1,"amount":5.0}
        check("rotate", executor.apply_step(r))
        check("rotated", not executor.nodes[1145].transform.is_equal_approx(baseline))
        var saved = executor.snapshot()
        check("snapshot_one", saved["applied"].size() == 1)
        executor.reset_baseline()
        check("reset", executor.nodes[1145].transform.is_equal_approx(baseline))
        check("restore", executor.replay_snapshot(saved))
        var once: Transform3D = executor.nodes[1145].transform
        check("restore_idempotent", executor.replay_snapshot(saved) and executor.nodes[1145].transform.is_equal_approx(once))
        check("invalid_rejected", not executor.apply_step({"target_id":99999,"opcode":0x17,"axis":1,"amount":1.0}))
        var inv = {"target_id":1145,"opcode":0x17,"axis":1,"amount":-5.0}
        check("inverse", executor.apply_step(inv))
        check("inverse_baseline", executor.nodes[1145].transform.is_equal_approx(baseline))
        var shift = {"target_id":1148,"opcode":0x18,"axis":0,"amount":3.0}
        var before: Vector3 = executor.nodes[1148].position
        check("translate", executor.apply_step(shift))
        check("translate_delta", executor.nodes[1148].position.is_equal_approx(before + Vector3(3,0,0)))
    executor.queue_free()
    scene.queue_free()
    var result = {"status":"PASS" if failed.is_empty() else "FAIL","checks":checks,"failed":failed,"scope":"experimental local-space transform executor; axis/pivot/time original fidelity HOLD"}
    print("OPENAZRAEL_C8_EXECUTOR_V355 " + JSON.stringify(result))
    quit(0 if failed.is_empty() else 1)