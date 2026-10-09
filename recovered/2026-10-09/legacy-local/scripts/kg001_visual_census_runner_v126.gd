extends SceneTree
const ROOM_PATHS={"R1":"res://assets/rooms/R1.glb","R7":"res://assets/rooms/R7.glb","R8":"res://assets/rooms/R8.glb"}
const SIZE:=Vector2i(512,512)
var failures:Array[String]=[]
var evidence:Dictionary={}
var checks:=0

func _check(name:String,ok:bool)->void:
    checks+=1
    if not ok: failures.append(name)
func _settle(n:int=2)->void:
    for _i in range(n): await process_frame

func _walk(n:Node,out:Array[Node])->void:
    out.append(n)
    for c in n.get_children(): _walk(c,out)
func _find(n:Node,wanted:String)->Node:
    if String(n.name)==wanted: return n
    for c in n.get_children():
        var f:=_find(c,wanted)
        if f!=null:return f
    return null

func _prepare_geometry(root_node:Node,hidden:Array)->AABB:
    var nodes:Array[Node]=[]; _walk(root_node,nodes)
    var hide:Dictionary={}
    for name in hidden: hide[String(name)]=true
    var mat:=StandardMaterial3D.new()
    mat.shading_mode=BaseMaterial3D.SHADING_MODE_UNSHADED
    mat.albedo_color=Color(0.92,0.92,0.92,1.0)
    var have:=false; var box:=AABB()
    for node in nodes:
        if not node is MeshInstance3D: continue
        var mi:=node as MeshInstance3D
        if hide.has(String(mi.name)): mi.visible=false
        if not mi.visible or mi.mesh==null: continue
        mi.material_override=mat
        var a:=mi.get_aabb()
        for x in [a.position.x,a.end.x]:
            for y in [a.position.y,a.end.y]:
                for z in [a.position.z,a.end.z]:
                    var p:=mi.global_transform*Vector3(x,y,z)
                    if not have: box=AABB(p,Vector3.ZERO); have=true
                    else: box=box.expand(p)
    return box

func _camera_pose(box:AABB,index:int)->Dictionary:
    var center:=box.get_center()
    var span:=maxf(1.0,maxf(box.size.x,maxf(box.size.y,box.size.z)))
    var dirs=[
        Vector3(1.25,0.85,1.25).normalized(),
        Vector3(-1.20,0.75,1.10).normalized(),
        Vector3(0.20,1.55,-1.10).normalized(),
    ]
    return {"pos":center+dirs[index]*span*1.75,"target":center}

func _render_room(room:Node,hidden:Array,view_index:int,label:String)->Dictionary:
    var vp:=SubViewport.new()
    vp.size=SIZE
    vp.render_target_update_mode=SubViewport.UPDATE_ALWAYS
    vp.transparent_bg=false
    root.add_child(vp)
    vp.add_child(room)
    var box:=_prepare_geometry(room,hidden)
    var cam:=Camera3D.new(); vp.add_child(cam); cam.current=true; cam.fov=52.0
    var pose:=_camera_pose(box,view_index)
    cam.global_position=pose["pos"]; cam.look_at(pose["target"],Vector3.UP)
    await _settle(3)
    await RenderingServer.frame_post_draw
    var image:=vp.get_texture().get_image()
    var data:=image.get_data()
    var sha:=data.sha256_text()
    var dir:=ProjectSettings.globalize_path("user://kg001_visual_v126")
    DirAccess.make_dir_recursive_absolute(dir)
    var path:=dir+"/"+label+"_v"+str(view_index)+".png"
    image.save_png(path)
    vp.queue_free(); await _settle(1)
    return {"sha256":sha,"png":path,"bounds":[box.position.x,box.position.y,box.position.z,box.size.x,box.size.y,box.size.z]}

func _run()->void:
    if DisplayServer.get_name()=="headless":
        print("OPENAZRAEL_KG001_VISUAL_CENSUS_V126 "+JSON.stringify({"status":"BLOCKED_GRAPHICAL_RENDER_REQUIRED"})); quit(2); return
    var vis=JSON.parse_string(FileAccess.get_file_as_string("res://data/tests/kg001_object_visibility_contract_v123.json"))
    _check("visibility_contract",vis is Dictionary)
    var state=root.get_node_or_null("DemoState"); _check("state",state!=null)
    var main=load("res://main.tscn"); _check("main",main is PackedScene)
    if state==null or not main is PackedScene: _finish(); return
    var scene=main.instantiate(); root.add_child(scene); await _settle(3)
    var manager=scene.get_node_or_null("RoomManager"); _check("manager",manager!=null)
    if manager==null: _finish(scene); return
    for room_id in ["R1","R7","R8"]:
        state.reset_all(); manager.load_room(room_id,false); await _settle()
        var hidden:Array=vis["fresh_state"][room_id]["expected_hidden_meshes"]
        var packed=load(ROOM_PATHS[room_id]); _check(room_id+"_direct_load",packed is PackedScene)
        if not packed is PackedScene: continue
        evidence[room_id]=[]
        for view_index in range(3):
            var direct=packed.instantiate()
            var ref=await _render_room(direct,hidden,view_index,room_id+"_direct")
            var runtime_clone=manager.current_room.duplicate()
            var actual=await _render_room(runtime_clone,hidden,view_index,room_id+"_runtime")
            var equal=String(ref["sha256"])==String(actual["sha256"])
            _check(room_id+"_view_"+str(view_index)+"_pixel_fingerprint",equal)
            evidence[room_id].append({"view":view_index,"equal":equal,"direct":ref,"runtime":actual})
    _finish(scene)

func _finish(scene:Node=null)->void:
    var out={"schema":"openazrael.kg001.visual_census","version":126,"status":"PASS" if failures.is_empty() else "FAIL","checks":checks,"failed":failures,"evidence":evidence,"reference":"direct canonical GLB; no AI or invented geometry"}
    print("OPENAZRAEL_KG001_VISUAL_CENSUS_V126 "+JSON.stringify(out))
    if scene!=null: scene.queue_free()
    quit(0 if failures.is_empty() else 1)
func _initialize()->void: call_deferred("_run")
