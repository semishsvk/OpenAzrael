extends SceneTree
const H = preload("res://scripts/validation/room_fidelity_helpers.gd")
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
        print("OPENAZRAEL_KG001_MATERIAL_TEXTURE_V124 "+JSON.stringify({"status":"BLOCKED_MISSING_FIDELITY_MANIFEST"})); quit(2); return
    var packed=load("res://main.tscn")
    _check("main_scene",packed is PackedScene)
    if not packed is PackedScene: _finish(); return
    var scene=packed.instantiate(); root.add_child(scene); await _settle(3)
    var manager=scene.get_node_or_null("RoomManager")
    var state=root.get_node_or_null("DemoState")
    _check("manager",manager!=null); _check("state",state!=null)
    if manager==null or state==null: _finish(scene); return
    var quantum=float(manifest.get("quantization",0.00001))
    for room_id in ["R1","R7","R8"]:
        state.reset_all(); manager.load_room(room_id,false); await _settle()
        var actual:=H.room_mesh_map(manager.current_room)
        var expected:Array=manifest["rooms"][room_id]["meshes"]
        var expected_names:Array[String]=[]
        for spec in expected: expected_names.append(String(spec["node"]))
        expected_names.sort()
        var actual_names:Array[String]=[]
        for name in actual.keys(): actual_names.append(String(name))
        actual_names.sort()
        _check(room_id+"_exact_mesh_set",actual_names==expected_names)
        var room_result={"meshes":actual_names.size(),"material_failures":0,"uv_failures":0}
        for spec in expected:
            var name:=String(spec["node"])
            var mi=actual.get(name)
            _check(room_id+"/"+name+"_exists",mi is MeshInstance3D)
            if not mi is MeshInstance3D: continue
            _check(room_id+"/"+name+"_single_surface",mi.mesh.get_surface_count()==1)
            _check(room_id+"/"+name+"_triangles",H.mesh_triangle_count(mi.mesh)==int(spec["triangles"]))
            var uv:=H.quantized_uv_sha(mi,quantum)
            var uv_ok=int(uv["count"])==int(spec["uv_count"]) and String(uv["sha256"])==String(spec["uv_sha256"])
            _check(room_id+"/"+name+"_uv_parity",uv_ok)
            if not uv_ok: room_result["uv_failures"]=int(room_result["uv_failures"])+1
            if mi.mesh.get_surface_count()>0:
                var mat=mi.get_active_material(0)
                _check(room_id+"/"+name+"_material_present",mat!=null)
                if mat!=null:
                    var mat_ok=String(mat.resource_name)==String(spec.get("material",""))
                    _check(room_id+"/"+name+"_material_name",mat_ok)
                    if not mat_ok: room_result["material_failures"]=int(room_result["material_failures"])+1
                    if spec.get("texture")!=null:
                        _check(room_id+"/"+name+"_base_material",mat is BaseMaterial3D)
                        if mat is BaseMaterial3D:
                            var bm:=mat as BaseMaterial3D
                            _check(room_id+"/"+name+"_texture_present",bm.albedo_texture!=null)
                            _check(room_id+"/"+name+"_non_metallic",is_zero_approx(bm.metallic))
                            if bool(spec.get("legacy_colorkey",false)):
                                _check(room_id+"/"+name+"_colorkey_enabled",bm.transparency!=BaseMaterial3D.TRANSPARENCY_DISABLED)
        summary[room_id]=room_result
    _finish(scene)

func _finish(scene:Node=null)->void:
    var out={"schema":"openazrael.kg001.material_texture_parity","version":124,"status":"PASS" if failures.is_empty() else "FAIL","checks":checks,"failed":failures,"rooms":summary}
    print("OPENAZRAEL_KG001_MATERIAL_TEXTURE_V124 "+JSON.stringify(out))
    if scene!=null: scene.queue_free()
    quit(0 if failures.is_empty() else 1)

func _initialize()->void: call_deferred("_run")
