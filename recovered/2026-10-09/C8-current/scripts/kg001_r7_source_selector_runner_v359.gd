extends SceneTree
const Selector = preload("res://scripts/r7_source_action_selector_v359.gd")
var failed: Array[String] = []
var checks := 0
func check(label: String, ok: bool) -> void:
    checks += 1
    if not ok: failed.append(label)
func _initialize() -> void: call_deferred("run_test")
func run_test() -> void:
    var ir = Selector.load_ir()
    check("source_bound",not ir.is_empty())
    var a = Selector.source_step_actions(0)
    var b = Selector.source_step_actions(1)
    var c = Selector.source_step_actions(2)
    check("two_per_step",a.size()==2 and b.size()==2 and c.size()==2)
    if a.size()==2 and b.size()==2 and c.size()==2:
        check("lever_pull_first",int(a[0]["target_id"])==1145 and float(a[0]["operand"])==1.0)
        check("lever_push_last",int(c[0]["target_id"])==1145 and float(c[0]["operand"])==-1.0)
        check("wheel",int(b[0]["target_id"])==100 and int(b[0]["opcode"])==23)
        check("reverse_sign",float(a[0]["operand"])+float(c[0]["operand"])==0.0)
        check("steps",int(a[0]["steps"])==15 and int(b[0]["steps"])==10)
    check("invalid_step",Selector.source_step_actions(99).is_empty())
    check("opposite_slot",Selector.select_actions(16,1).size()==2)
    var out={"status":"PASS" if failed.is_empty() else "FAIL","checks":checks,"failed":failed,"scope":"source-bound node/slot action selection, not proven original trigger mapping"}
    print("OPENAZRAEL_C8_SELECTOR_V359 "+JSON.stringify(out))
    quit(0 if failed.is_empty() else 1)