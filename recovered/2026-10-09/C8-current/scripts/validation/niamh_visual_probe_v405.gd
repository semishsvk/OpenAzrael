extends SceneTree
# Exploratory actual Godot GPU Niamh scene captures from canonical imported
# demo room/character assets. Original camera registration NOT yet calibrated.
var failed: Array[String] = []
var checks := 0
var shots: Array[Dictionary] = []

func ck(name: String, good: bool) -> void:
    checks += 1
    if not good:
        failed.append(name)

func sha(data: PackedByteArray) -> String:
    var h=HashingContext.new()
    h.start(HashingContext.HASH_SHA256)
    h.update(data)
    return h.finish().hex_encode()

func _initialize() -> void:
    call_deferred("_run")

func _capture(name: String) -> void:
    await process_frame
    await RenderingServer.frame_post_draw
    var img: Image = root.get_viewport().get_texture().get_image()
    img.convert(Image.FORMAT_RGB8)
    var filename="res://.tmp/"+name+".png"
    var code=img.save_png(filename)
    var pixels=sha(img.get_data())
    ck("saved_"+name,code==OK and img.get_width()==640 and img.get_height()==480)
    shots.append({"name":name,"path":filename,"width":img.get_width(),
       "height":img.get_height(),"pixel_rgb_sha256":pixels,"image_saved":code==OK})

func _run() -> void:
    root.get_window().size=Vector2i(640,480)
    var packed=load("res://main.tscn") as PackedScene
    ck("packed_exists",packed!=null)
    if packed==null:
        _done(null)
        return
    var main=packed.instantiate()
    root.add_child(main)
    await process_frame
    await process_frame
    # Hide overlays; only Niamh character/world composition examined
    for n in main.get_children():
        if n is CanvasLayer:
            n.visible=false
    var m=main.get_node("RoomManager")
    m.transition_cooldown=999.0
    m.load_room("R7",false)
    await process_frame
    m._on_character_animation_requested({
        "character":"Niamh","family":"NOLOOP1","target_object":"nibody",
        "source_required":true,"next_family":"REST"
    })
    var model=m.current_room.find_child("SourceCharacter_Niamh",true,false)
    ck("source_niamh_root",model!=null)
    if model==null:
        _done(main)
        return
    var anim=model.get_node_or_null("SourceCharacterAnimation") as AnimationPlayer
    ck("source_anim_player",anim!=null)
    if anim==null:
        _done(main)
        return
    var cameras=[
        {"id":"plus_z","offset":Vector3(0,12,190)},
        {"id":"minus_z","offset":Vector3(0,12,-190)},
        {"id":"plus_x","offset":Vector3(190,12,0)},
        {"id":"minus_x","offset":Vector3(-190,12,0)}
    ]
    var anchor: Vector3=model.global_position
    var target=anchor+Vector3(0,-20,0)
    var camera=Camera3D.new()
    camera.name="NIAMH_VISUAL_PROBE_CAMERA"
    camera.fov=65.0
    camera.near=.05
    camera.far=1000.0
    m.current_room.add_child(camera)
    var orig=main.get_node_or_null("Player/Camera3D") as Camera3D
    if orig!=null:
        orig.current=false
    camera.current=true
    for a in cameras:
        var id=String(a["id"])
        camera.global_position=anchor+Vector3(0,-14,0)+a["offset"]
        camera.look_at(target,Vector3.UP)
        anim.play(&"NOLOOP1")
        anim.seek(0,true)
        await _capture("niamh_probe_"+id+"_frame0")
        anim.seek(10.0/15.0,true)
        await _capture("niamh_probe_"+id+"_source_frame10")
        anim.play(&"REST")
        anim.seek(0.0,true)
        await _capture("niamh_probe_"+id+"_rest")
    camera.queue_free()
    _done(main)

func _done(main: Node) -> void:
    if main!=null:
        main.queue_free()
    await process_frame
    await process_frame
    var result={
        "schema":"openazrael.c8.niamh_experimental_visual_probe.v405",
        "status":"PASS" if failed.is_empty() else "FAIL",
        "checks":checks,"failed":failed,"captures":shots,
        "source_model":"Niamh.glb",
        "source_motion":"NOLOOP1 frame0 to frame10 and REST",
        "camera_registration":"UNVERIFIED_EXPLORATORY_RING",
        "original_visual_fidelity":"HOLD"
    }
    var f=FileAccess.open("res://.tmp/niamh_visual_probe_v405.json",FileAccess.WRITE)
    if f:
        f.store_string(JSON.stringify(result,"  "))
        f.close()
    print("NIAMH_RENDER_PROBE_V405 "+JSON.stringify({
      "status":result["status"],"checks":checks,
      "captures":shots.size(),"failed":failed,
      "fidelity":"HOLD_UNCALIBRATED_CAMERA"}))
    quit(0 if failed.is_empty() else 1)