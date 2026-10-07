extends SceneTree
const Controller=preload("res://scripts/eugene_controller_v193.gd")
var failed:Array[String]=[]
func ck(v:bool,n:String)->void:
    if not v: failed.append(n)
func _initialize()->void: call_deferred("_run")
func _forward(n:Node3D)->Vector3:
    return (n.global_transform.basis * Vector3.RIGHT).normalized()
func _run()->void:
    var n=Controller.new(); root.add_child(n)
    n.call("_apply_source_facing",Vector3.RIGHT)
    ck(_forward(n).dot(Vector3.RIGHT)>0.999,"plus_x")
    n.call("_apply_source_facing",Vector3.FORWARD)
    ck(_forward(n).dot(Vector3.FORWARD)>0.999,"forward_minus_z")
    n.call("_apply_source_facing",Vector3.LEFT)
    ck(_forward(n).dot(Vector3.LEFT)>0.999,"minus_x")
    n.call("_apply_source_facing",Vector3.BACK)
    ck(_forward(n).dot(Vector3.BACK)>0.999,"back_plus_z")
    print("OPENAZRAEL_EUGENE_FACING_V254 "+JSON.stringify({"status":"PASS" if failed.is_empty() else "FAIL","failed":failed}))
    quit(0 if failed.is_empty() else 1)
