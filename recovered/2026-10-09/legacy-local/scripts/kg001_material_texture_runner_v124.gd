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
        # v133 proves source XAF -> canonical GLB identity. At runtime, compare
        # production RoomManager loading against a direct Godot import of the
        # exact same pinned GLB so importer-internal vertex/material rewrites do
        # not masquerade as source-fidelity failures.
        var asset_path:=String(manifest["rooms"][room_id]["asset_path"])
        var direct_packed=load("res://"+asset_path)
        _check(room_id+"_direct_asset",direct_packed is PackedScene)
        if not direct_packed is PackedScene:
            continue
        var direct_root=(direct_packed as PackedScene).instantiate()
        var direct:=H.room_mesh_map(direct_root)
        var expected:Array=manifest["rooms"][room_id]["meshes"]
        var expected_names:Array[String]=[]
        for spec in expected: expected_names.append(String(spec["node"]))
        expected_names.sort()
        var actual_names:Array[String]=[]
        for name in actual.keys(): actual_names.append(String(name))
        actual_names.sort()
        var direct_names:Array[String]=[]
        for name in direct.keys():
            direct_names.append(String(name))
        direct_names.sort()
        _check(room_id+"_exact_mesh_set",actual_names==expected_names)
        _check(room_id+"_direct_mesh_set",direct_names==expected_names)
        var room_result={"meshes":actual_names.size(),"material_failures":0,"uv_failures":0}
        for spec in expected:
            var name:=String(spec["node"])
            var mi=actual.get(name)
            var ref_mi=direct.get(name)
            _check(room_id+"/"+name+"_exists",mi is MeshInstance3D)
            _check(room_id+"/"+name+"_direct_exists",ref_mi is MeshInstance3D)
            if not mi is MeshInstance3D or not ref_mi is MeshInstance3D:
                continue
            _check(room_id+"/"+name+"_single_surface",mi.mesh.get_surface_count()==1)
            _check(room_id+"/"+name+"_triangles",H.mesh_triangle_count(mi.mesh)==int(spec["triangles"]))
            var uv:=H.quantized_uv_sha(mi,quantum)
            var ref_uv:=H.quantized_uv_sha(ref_mi,quantum)
            var uv_ok=(
                int(uv["count"])==int(spec["uv_count"])
                and int(ref_uv["count"])==int(spec["uv_count"])
                and String(uv["sha256"])==String(ref_uv["sha256"])
            )
            _check(room_id+"/"+name+"_uv_runtime_import_parity",uv_ok)
            if not uv_ok: room_result["uv_failures"]=int(room_result["uv_failures"])+1
            if mi.mesh.get_surface_count()>0:
                var mat=mi.get_active_material(0)
                var ref_mat=ref_mi.get_active_material(0)
                _check(room_id+"/"+name+"_material_present",mat!=null)
                _check(room_id+"/"+name+"_direct_material_present",ref_mat!=null)
                if mat!=null and ref_mat!=null:
                    var mat_ok=(
                        mat.get_class()==ref_mat.get_class()
                        and String(mat.resource_name)==String(ref_mat.resource_name)
                    )
                    _check(room_id+"/"+name+"_material_runtime_import_parity",mat_ok)
                    if not mat_ok:
                        room_result["material_failures"]=int(room_result["material_failures"])+1
                    if spec.get("texture")!=null:
                        _check(
                            room_id+"/"+name+"_base_material",
                            mat is BaseMaterial3D and ref_mat is BaseMaterial3D
                        )
                        if mat is BaseMaterial3D and ref_mat is BaseMaterial3D:
                            var bm:=mat as BaseMaterial3D
                            var rbm:=ref_mat as BaseMaterial3D
                            _check(room_id+"/"+name+"_texture_present",bm.albedo_texture!=null)
                            _check(room_id+"/"+name+"_direct_texture_present",rbm.albedo_texture!=null)
                            if bm.albedo_texture!=null and rbm.albedo_texture!=null:
                                _check(
                                    room_id+"/"+name+"_texture_pixels_runtime_import_parity",
                                    H.texture_rgba_sha(bm.albedo_texture)
                                    == H.texture_rgba_sha(rbm.albedo_texture)
                                )
                            _check(room_id+"/"+name+"_non_metallic",is_zero_approx(bm.metallic))
                            if bool(spec.get("legacy_colorkey",false)):
                                _check(
                                    room_id+"/"+name+"_colorkey_enabled",
                                    bm.transparency!=BaseMaterial3D.TRANSPARENCY_DISABLED
                                )
        direct_root.free()
        summary[room_id]=room_result
    _finish(scene)

func _finish(scene:Node=null)->void:
    var out={"schema":"openazrael.kg001.material_texture_parity","version":124,"status":"PASS" if failures.is_empty() else "FAIL","checks":checks,"failed":failures,"rooms":summary}
    print("OPENAZRAEL_KG001_MATERIAL_TEXTURE_V124 "+JSON.stringify(out))
    if scene!=null: scene.queue_free()
    quit(0 if failures.is_empty() else 1)

func _initialize()->void: call_deferred("_run")
