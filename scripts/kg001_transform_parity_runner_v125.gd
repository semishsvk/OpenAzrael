extends SceneTree
const H = preload("res://scripts/validation/room_fidelity_helpers.gd")
const TRANSFORM_TOL:=0.0001
const BOUNDS_TOL:=0.001
var failures:Array[String]=[]
var checks:=0
var summary:Dictionary={}

func _check(name:String,ok:bool)->void:
    checks+=1
    if not ok: failures.append(name)
func _settle(n:int=2)->void:
    for _i in range(n): await process_frame

func _run()->void:
    var manifest:=H.load_manifest()
    if manifest.is_empty():
        print("OPENAZRAEL_KG001_TRANSFORM_V125 "+JSON.stringify({"status":"BLOCKED_MISSING_FIDELITY_MANIFEST"})); quit(2); return
    var packed=load("res://main.tscn"); _check("main_scene",packed is PackedScene)
    if not packed is PackedScene: _finish(); return
    var scene=packed.instantiate(); root.add_child(scene); await _settle(3)
    var manager=scene.get_node_or_null("RoomManager"); var state=root.get_node_or_null("DemoState")
    _check("manager",manager!=null); _check("state",state!=null)
    if manager==null or state==null: _finish(scene); return
    for room_id in ["R1","R7","R8"]:
        state.reset_all(); manager.load_room(room_id,false); await _settle()
        var actual:=H.room_mesh_map(manager.current_room)
        var tfail:=0; var bfail:=0
        for spec in manifest["rooms"][room_id]["meshes"]:
            var name:=String(spec["node"]); var mi=actual.get(name)
            _check(room_id+"/"+name+"_exists",mi is MeshInstance3D)
            if not mi is MeshInstance3D: continue
            var tok:=H.arrays_close(H.transform_values(mi.global_transform),spec["transform"],TRANSFORM_TOL)
            var bok:=H.arrays_close(H.bounds_values(mi.get_aabb()),spec["bounds"],BOUNDS_TOL)
            _check(room_id+"/"+name+"_transform",tok); _check(room_id+"/"+name+"_bounds",bok)
            if not tok: tfail+=1
            if not bok: bfail+=1
        summary[room_id]={"transform_failures":tfail,"bounds_failures":bfail}
    _finish(scene)

func _finish(scene:Node=null)->void:
    var out={"schema":"openazrael.kg001.transform_parity","version":125,"status":"PASS" if failures.is_empty() else "FAIL","checks":checks,"failed":failures,"rooms":summary}
    print("OPENAZRAEL_KG001_TRANSFORM_V125 "+JSON.stringify(out))
    if scene!=null: scene.queue_free()
    quit(0 if failures.is_empty() else 1)
func _initialize()->void: call_deferred("_run")
