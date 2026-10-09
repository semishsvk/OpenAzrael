extends SceneTree
# Actual Godot renderer occlusion study:
# normal scene, normal without Niamh, Niamh-only, empty.
# Comparison is scoped and does not alter production materials or object depth.
var fails: Array[String] = []
var checks := 0
var artifacts: Array[Dictionary] = []

func ck(n: String, condition: bool) -> void:
    checks += 1
    if not condition:
        fails.append(n)

func _initialize() -> void:
    call_deferred("_run")

func _walk(node: Node, models: Node3D, out: Array[MeshInstance3D]) -> void:
    for child in node.get_children():
        if child is MeshInstance3D and child!=models and not models.is_ancestor_of(child):
            out.append(child as MeshInstance3D)
        _walk(child,models,out)

func _save(name: String) -> void:
    await process_frame
    await RenderingServer.frame_post_draw
    var img=root.get_viewport().get_texture().get_image()
    img.convert(Image.FORMAT_RGB8)
    var file="res://.tmp/niamh_occlusion_"+name+".png"
    var result=img.save_png(file)
    ck("png_"+name,result==OK and img.get_size()==Vector2i(640,480))
    artifacts.append({"path":file,"name":name,"width":img.get_width(),"height":img.get_height()})

func _run() -> void:
    root.get_window().size=Vector2i(640,480)
    var main=(load("res://main.tscn") as PackedScene).instantiate()
    root.add_child(main)
    await process_frame
    await process_frame
    for child in main.get_children():
        if child is CanvasLayer:
            child.visible=false
    var manager=main.get_node("RoomManager")
    manager.transition_cooldown=999.0
    manager.load_room("R7",false)
    await process_frame
    manager._on_character_animation_requested({
        "character":"Niamh","family":"NOLOOP1","target_object":"nibody",
        "source_required":true,"next_family":"REST"
    })
    var model=manager.current_room.find_child("SourceCharacter_Niamh",true,false) as Node3D
    ck("char_exists",model!=null)
    if model==null:
        _finish(main,{})
        return
    var ap=model.get_node("SourceCharacterAnimation") as AnimationPlayer
    ap.play(&"REST")
    ap.seek(0.0,true)
    var world_parts: Array[MeshInstance3D]=[]
    _walk(manager.current_room,model,world_parts)
    ck("world_meshes_found",world_parts.size()>20)
    var model_parts: Array[MeshInstance3D]=[]
    _walk_model(model,model_parts)
    ck("model_meshes_found",model_parts.size()>2)
    var mats: Array[Dictionary]=[]
    for part in model_parts:
        for i in part.mesh.get_surface_count() if part.mesh!=null else 0:
            var mat=part.get_active_material(i) as BaseMaterial3D
            if mat!=null:
                mats.append({"node":str(part.get_path()),"surface":i,
                    "transparency":int(mat.transparency),
                    "depth_draw_mode":int(mat.depth_draw_mode),
                    "blend_mode":int(mat.blend_mode),
                    "no_depth_test":mat.no_depth_test,
                    "render_priority":mat.render_priority,
                    "albedo_alpha":mat.albedo_color.a,
                    "texture":mat.albedo_texture.resource_path if mat.albedo_texture!=null else ""})
    var camera=Camera3D.new()
    camera.name="R7_OCCLUSION_RECON_CAMERA"
    camera.fov=65.0
    camera.near=.05
    camera.far=1500
    manager.current_room.add_child(camera)
    var player_camera=main.get_node_or_null("Player/Camera3D") as Camera3D
    if player_camera!=null:
        player_camera.current=false
    camera.current=true
    var rootpos: Vector3=model.global_position
    for spec in [
      {"direction":"plus_z","offset":Vector3(0,12,190)},
      {"direction":"minus_z","offset":Vector3(0,12,-190)}
    ]:
        var tag=String(spec["direction"])
        camera.global_position=rootpos+Vector3(0,-14,0)+spec["offset"]
        camera.look_at(rootpos+Vector3(0,-20,0),Vector3.UP)
        for o in world_parts:
            o.visible=true
        model.visible=true
        await _save(tag+"_world_with_character")
        model.visible=false
        await _save(tag+"_world_without_character")
        for o in world_parts:
            o.visible=false
        model.visible=true
        await _save(tag+"_character_only")
        model.visible=false
        await _save(tag+"_empty")
    var report={"schema":"openazrael.c8.niamh_occlusion_renderer.v406",
        "status":"PASS" if fails.is_empty() else "FAIL","checks":checks,"failed":fails,
        "world_meshes":world_parts.size(),"character_meshes":model_parts.size(),
        "material_properties":mats,
        "images":artifacts,
        "camera":"UNREGISTERED_PLUS_MINUS_Z_EXPLORATION",
        "original_runtime_fidelity":"HOLD"}
    _finish(main,report)

func _walk_model(n: Node, out: Array[MeshInstance3D]) -> void:
    if n is MeshInstance3D:
        out.append(n as MeshInstance3D)
    for child in n.get_children():
        _walk_model(child,out)

func _finish(main: Node, report: Dictionary) -> void:
    if main!=null:
        main.queue_free()
    await process_frame
    await process_frame
    if report.is_empty():
        report={"status":"FAIL","failed":fails}
    var file=FileAccess.open("res://.tmp/niamh_occlusion_probe_v406.json",FileAccess.WRITE)
    if file:
        file.store_string(JSON.stringify(report,"  "))
        file.close()
    print("NIAMH_OCCLUSION_V406 "+JSON.stringify({"status":report["status"],
        "checks":checks,"failed":fails,"character_meshes":report.get("character_meshes",0),
        "world_meshes":report.get("world_meshes",0),"captures":artifacts.size()}))
    quit(0 if fails.is_empty() else 1)