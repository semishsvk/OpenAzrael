extends SceneTree
const H=preload("res://scripts/validation/room_fidelity_helpers.gd")
const ASSET_MANIFEST:="res://data/runtime_generated/runtime_asset_manifest_v128.json"
const VIS_POLICY:="res://data/runtime_visibility_policy_v123.json"
const T_TOL:=0.0001
const B_TOL:=0.001
var failures:Array[String]=[]
var checks:=0
var rooms:Dictionary={}
func _check(n:String,ok:bool)->void:
    checks+=1
    if not ok:failures.append(n)
func _settle(n:int=1)->void:
    for _i in range(n):await process_frame
func _sha_bytes(path:String)->String:
    var ctx:=HashingContext.new();ctx.start(HashingContext.HASH_SHA256);ctx.update(FileAccess.get_file_as_bytes(path));return ctx.finish().hex_encode()

func _run()->void:
    if not FileAccess.file_exists(ASSET_MANIFEST) or not FileAccess.file_exists(H.MANIFEST_PATH) or not FileAccess.file_exists(VIS_POLICY):
        print("OPENAZRAEL_KG001_PACKAGED_PARITY_V128 "+JSON.stringify({"status":"FAIL","reason":"PACKAGED_METADATA_MISSING"}));quit(1);return
    var asset_manifest=JSON.parse_string(FileAccess.get_file_as_string(ASSET_MANIFEST))
    var fidelity=H.load_manifest()
    var vis=JSON.parse_string(FileAccess.get_file_as_string(VIS_POLICY))
    _check("metadata_valid",asset_manifest is Dictionary and fidelity is Dictionary and vis is Dictionary)
    for rel in asset_manifest["files"].keys():
        var path:="res://"+String(rel)
        var spec:Dictionary=asset_manifest["files"][rel]
        _check("asset_exists:"+String(rel),FileAccess.file_exists(path))
        if FileAccess.file_exists(path):
            var bytes:=FileAccess.get_file_as_bytes(path)
            _check("asset_bytes:"+String(rel),bytes.size()==int(spec["bytes"]))
            _check("asset_sha:"+String(rel),_sha_bytes(path)==String(spec["sha256"]))
    var state=root.get_node_or_null("DemoState");var packed=load("res://main.tscn")
    _check("state",state!=null);_check("main",packed is PackedScene)
    if state==null or not packed is PackedScene:_finish();return
    var scene=packed.instantiate();root.add_child(scene);await _settle(2)
    var manager=scene.get_node_or_null("RoomManager");_check("manager",manager!=null)
    if manager==null:_finish(scene);return
    var quantum=float(fidelity["quantization"])
    for room_id in ["R1","R7","R8"]:
        state.reset_all();manager.load_room(room_id,false);await _settle()
        var actual:=H.room_mesh_map(manager.current_room)
        var expected:Array=fidelity["rooms"][room_id]["meshes"]
        _check(room_id+"_mesh_count",actual.size()==int(fidelity["rooms"][room_id]["mesh_count"]))
        var room_fail:=0
        for spec in expected:
            var name:=String(spec["node"]);var mi=actual.get(name)
            _check(room_id+"/"+name+"_exists",mi is MeshInstance3D)
            if not mi is MeshInstance3D:room_fail+=1;continue
            _check(room_id+"/"+name+"_triangles",H.mesh_triangle_count(mi.mesh)==int(spec["triangles"]))
            var uv:=H.quantized_uv_sha(mi,quantum)
            _check(room_id+"/"+name+"_uv",int(uv["count"])==int(spec["uv_count"]) and String(uv["sha256"])==String(spec["uv_sha256"]))
            _check(room_id+"/"+name+"_transform",H.arrays_close(H.transform_values(mi.global_transform),spec["transform"],T_TOL))
            _check(room_id+"/"+name+"_bounds",H.arrays_close(H.bounds_values(mi.get_aabb()),spec["bounds"],B_TOL))
            if mi.mesh.get_surface_count()>0:
                var mat=mi.get_active_material(0)
                _check(room_id+"/"+name+"_material",mat!=null and String(mat.resource_name)==String(spec.get("material","")))
                if spec.get("texture")!=null:
                    _check(room_id+"/"+name+"_texture",mat is BaseMaterial3D and (mat as BaseMaterial3D).albedo_texture!=null)
        for hidden_name in vis["fresh_hidden"][room_id]:
            var node=actual.get(String(hidden_name));_check(room_id+"/hidden/"+String(hidden_name),node is MeshInstance3D and not (node as MeshInstance3D).is_visible_in_tree())
        for visible_name in vis["fresh_required_visible"][room_id]:
            var node=actual.get(String(visible_name));_check(room_id+"/visible/"+String(visible_name),node is MeshInstance3D and (node as MeshInstance3D).is_visible_in_tree())
        rooms[room_id]={"meshes":actual.size(),"failures":room_fail}
    _finish(scene)
func _finish(scene:Node=null)->void:
    var out={"schema":"openazrael.kg001.packaged_parity","version":128,"status":"PASS" if failures.is_empty() else "FAIL","checks":checks,"failed":failures,"rooms":rooms,"execution_boundary":"must run from exported EXE/PCK"}
    print("OPENAZRAEL_KG001_PACKAGED_PARITY_V128 "+JSON.stringify(out))
    if scene!=null:scene.queue_free()
    quit(0 if failures.is_empty() else 1)
func _initialize()->void:call_deferred("_run")
