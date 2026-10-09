extends SceneTree
const Scheduler = preload("res://scripts/r7_source_action_scheduler_v354.gd")
var failures: Array[String] = []
var checks := 0
func check(name: String, ok: bool) -> void:
    checks += 1
    if not ok:
        failures.append(name)
func _initialize() -> void:
    call_deferred("run_test")
func run_test() -> void:
    var a = Scheduler.new()
    root.add_child(a)
    check("reject_invalid", not a.enqueue(98, 0x19, 2, 1.0, 5))
    check("reject_zero", not a.enqueue(98, 0x17, 2, 1.0, 0))
    check("queue_rotation", a.enqueue(98, 0x17, 2, 5.0, 5))
    check("queue_translation", a.enqueue(1145, 0x18, 1, 1.0, 10))
    check("lifo", a.pending[0]["target_id"] == 1145)
    a.tick()
    check("tick_one", a.tick_index == 1)
    check("both_pending", a.pending.size() == 2)
    check("remaining_rotation", a.pending[1]["remaining"] == 4)
    var saved = a.snapshot()
    var b = Scheduler.new()
    root.add_child(b)
    check("restore", b.restore_snapshot(saved))
    check("roundtrip", JSON.stringify(b.snapshot()) == JSON.stringify(saved))
    check("reject_bad", not b.restore_snapshot({"version":1,"tick_index":2,"pending":[{"opcode":99,"remaining":1,"total":1}]}))
    check("reject_atomic", JSON.stringify(b.snapshot()) == JSON.stringify(saved))
    b.flush()
    check("flush_empty", b.pending.is_empty())
    check("flush_ticks", b.tick_index == 10)
    check("source_unchanged", a.pending.size() == 2)
    a.queue_free()
    b.queue_free()
    var out = {"schema":"openazrael.c8.scheduler.v354","status":"PASS" if failures.is_empty() else "FAIL","checks":checks,"failed":failures,"scope":"deterministic queue model; no original runtime fidelity claim"}
    print("OPENAZRAEL_C8_SCHEDULER " + JSON.stringify(out))
    quit(0 if failures.is_empty() else 1)