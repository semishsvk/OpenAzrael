extends SceneTree
# Bounded, experimental Niamh renderer variants; no production material changes.
# Evidence only. Camera intentionally fixed but NOT original-runtime registered.
var fail: Array[String]=[]
var checks:=0
var images: Array[Dictionary]=[]
var original_materials: Array[Dictionary]=[]

func ck(name: String, ok: bool) -> void:
    checks+=1
    if not ok:
        fail.append(name)
func _initialize() -> void:
    call_deferred("_run")

func _meshes(node: Node, all: Array[MeshInstance3D]) -> void:
    if node is MeshInstance3D:
        all.append(node)
    for child in node.get_children():
        _meshes(child,all)

func _shot(tag: String) -> void:
    await process_frame
    await RenderingServer.frame_post_draw
    var image=root.get_viewport().get_texture().get_image()
    image.convert(Image.FORMAT_RGB8)
    var path="res://.tmp/niamh_material_experiment_v407_"+tag+".png"
    var result=image.save_png(path)
    ck("capture_"+tag,result==OK and image.get_size()==Vector2i(640,480))
    images.append({"name":tag,"path":path,"saved":result==OK})

func _style(style: String) -> void:
    for x in original_materials:
        var m=x["mesh"] as MeshInstance3D
        var idx=int(x["surface"])
        var old=x["material"] as BaseMaterial3D
        var fresh=old.duplicate() as BaseMaterial3D
        if style in ["nodepth_opaque","nodepth_alpha"]:
            fresh.no_depth_test=true
            fresh.render_priority=20
        if style in ["nodepth_alpha","depth_alpha"]:
            fresh.transparency=BaseMaterial3D.TRANSPARENCY_ALPHA
            var a=fresh.albedo_color
            a.a=.62
            fresh.albedo_color=a
            fresh.render_priority=20
        m.set_surface_override_material(idx,fresh)

func _run() -> void:
    root.get_window().size=Vector2i(640,480)
    var main=(load("res://main.tscn") as PackedScene).instantiate()
    root.add_child(main)
    await process_frame
    await process_frame
    for n in main.get_children():
        if n is CanvasLayer:
            n.visible=false
    var manager=main.get_node("RoomManager")
    manager.transition_cooldown=999
    manager.load_room("R7",false)
    await process_frame
    manager._on_character_animation_requested({
      "character":"Niamh","family":"NOLOOP1","target_object":"nibody",
      "source_required":true,"next_family":"REST"})
    var model=manager.current_room.find_child("SourceCharacter_Niamh",true,false) as Node3D
    ck("source_character",model!=null)
    if model==null:
        _finish(main)
        return
    var anim=model.get_node("SourceCharacterAnimation") as AnimationPlayer
    anim.play(&"REST")
    anim.seek(0.0,true)
    var mesh_parts: Array[MeshInstance3D]=[]
    _meshes(model,mesh_parts)
    ck("nineteen_source_meshes",mesh_parts.size()==19)
    for m in mesh_parts:
        if m.mesh==null:
            continue
        for surface in range(m.mesh.get_surface_count()):
            var mat=m.get_active_material(surface) as BaseMaterial3D
            if mat!=null:
                original_materials.append({"mesh":m,"surface":surface,"material":mat})
    ck("all_source_materials_available",original_materials.size()==19)
    var origin=model.global_position
    var camera=Camera3D.new()
    camera.name="NIAMH_DEPTH_OPTION_PROBE"
    camera.fov=65
    camera.near=.05
    camera.far=1500
    manager.current_room.add_child(camera)
    var player_camera=main.get_node_or_null("Player/Camera3D") as Camera3D
    if player_camera!=null:
        player_camera.current=false
    camera.current=true
    for side in [
      {"id":"plus_z","offset":Vector3(0,12,190)},
      {"id":"minus_z","offset":Vector3(0,12,-190)}
    ]:
        var d=String(side["id"])
        camera.global_position=origin+Vector3(0,-14,0)+side["offset"]
        camera.look_at(origin+Vector3(0,-20,0),Vector3.UP)
        for style in ["baseline_opaque","nodepth_opaque","depth_alpha","nodepth_alpha"]:
            _style(style)
            await _shot(d+"_"+style)
        model.visible=false
        await _shot(d+"_background")
        model.visible=true
    _finish(main)

func _finish(main: Node) -> void:
    if main!=null:
        main.queue_free()
    await process_frame
    await process_frame
    var summary={"schema":"openazrael.c8.niamh_render_policy_experiment.v407",
     "status":"PASS" if fail.is_empty() else "FAIL","checks":checks,"failures":fail,
     "source_character_meshes":19,"original_surface_count":original_materials.size(),
     "material_styles":["baseline_opaque","nodepth_opaque","depth_alpha","nodepth_alpha"],
     "alpha_test":.62,"no_depth_is_experimental":true,"images":images,
     "camera":"EXPLORATORY_PLUS_MINUS_Z_NOT_REGISTERED",
     "original_visual_fidelity":"HOLD_SOURCE_GHOST_RENDER_MECHANISM_UNVERIFIED"}
    var f=FileAccess.open("res://.tmp/niamh_render_policy_v407.json",FileAccess.WRITE)
    if f:
        f.store_string(JSON.stringify(summary,"  "))
        f.close()
    print("NIAMH_RENDER_POLICY_V407 "+JSON.stringify({
      "status":summary["status"],"checks":checks,"failures":fail,
      "captured":images.size(),"fidelity":"HOLD",
      "production_materials_changed":false}))
    quit(0 if fail.is_empty() else 1)