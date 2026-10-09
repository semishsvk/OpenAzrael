extends SceneTree
# Candidate 8 camera registration probe using the ORIGINAL R.EXE DOSBox-X
# save-memory player/camera transform at 0x35B5E0/0x35B864.
# R7 original native framebuffer central 3D window is approx 552x280.
# Different vertical FOV options remain HYPOTHESES until capture comparison.
const NATIVE_ORIGINAL_EYE := Vector3(7.648281,4.204147,3.914586)
const NATIVE_FORWARD := Vector3(-0.91354546,0.0,0.40673664)
const ORIGINAL_FPS_UNKNOWN := true
var errors: Array[String]=[]
var count:=0
var photos: Array[Dictionary]=[]
func check(name: String, ok: bool) -> void:
    count+=1
    if not ok:
        errors.append(name)
func _initialize() -> void:
    call_deferred("_go")
func _capture(name: String) -> void:
    await process_frame
    await RenderingServer.frame_post_draw
    var capture=root.get_viewport().get_texture().get_image()
    capture.convert(Image.FORMAT_RGB8)
    var filename="res://.tmp/r7_native_camera_v408_"+name+".png"
    var saved=capture.save_png(filename)
    check("png_"+name,saved==OK and capture.get_size()==Vector2i(552,280))
    photos.append({"name":name,"path":filename,"width":capture.get_width(),
                   "height":capture.get_height()})
func _go() -> void:
    root.get_window().size=Vector2i(552,280)
    var scene=(load("res://main.tscn") as PackedScene).instantiate()
    root.add_child(scene)
    await process_frame
    await process_frame
    for n in scene.get_children():
        if n is CanvasLayer:
            n.visible=false
    var m=scene.get_node("RoomManager")
    m.transition_cooldown=999.0
    m.load_room("R7",false)
    await process_frame
    var camera=Camera3D.new()
    camera.name="R7_ORIGINAL_RAM_CAMERA_V408"
    camera.near=.05
    camera.far=2000
    m.current_room.add_child(camera)
    var original_camera=scene.get_node_or_null("Player/Camera3D") as Camera3D
    if original_camera!=null:
        original_camera.current=false
    camera.current=true
    camera.global_position=NATIVE_ORIGINAL_EYE
    camera.look_at(NATIVE_ORIGINAL_EYE+NATIVE_FORWARD,Vector3.UP)
    var world_dir=-camera.global_basis.z
    check("source_forward_matches_view",world_dir.distance_to(NATIVE_FORWARD)<.001)
    check("camera_memory_readback",camera.global_position.distance_to(NATIVE_ORIGINAL_EYE)<.001)
    for fov in [35,45,55,65,75,85,95,105]:
        camera.fov=float(fov)
        await _capture("background_fov_"+str(fov))
    # Source-animation geometry without changing production ghost renderer
    m._on_character_animation_requested({
        "character":"Niamh","family":"NOLOOP1",
        "target_object":"nibody","source_required":true,
        "next_family":"REST"})
    var model=m.current_room.find_child("SourceCharacter_Niamh",true,false) as Node3D
    check("source_model_anchored",model!=null)
    if model!=null:
        var ap=model.get_node("SourceCharacterAnimation") as AnimationPlayer
        ap.play(&"REST")
        ap.seek(0.0,true)
        for fov in [55,65,75,85]:
            camera.fov=float(fov)
            await _capture("opaque_niamh_fov_"+str(fov))
    var payload={"schema":"openazrael.c8.original_memory_camera_probe.v408",
     "status":"PASS" if errors.is_empty() else "FAIL",
     "checks":count,"failed":errors,
     "original_memory_eye_xyz":[NATIVE_ORIGINAL_EYE.x,NATIVE_ORIGINAL_EYE.y,NATIVE_ORIGINAL_EYE.z],
     "original_memory_look_unit":[NATIVE_FORWARD.x,NATIVE_FORWARD.y,NATIVE_FORWARD.z],
     "source_save_sha256":"7694f3c2edef8b47599b295624e751cd218ae53aadd9fe403aedcf28505ba650",
     "engine":"Godot 4.7.2 GL compatibility",
     "camera_fov_candidates":[35,45,55,65,75,85,95,105],
     "framing":"552x280 original 3D portal crop",
     "captures":photos,
     "fidelity":"HOLD_UNTIL_DIRECT_ORIGINAL_PERSPECTIVE_DIFF"}
    var f=FileAccess.open("res://.tmp/r7_camera_registration_probe_v408.json",FileAccess.WRITE)
    if f:
        f.store_string(JSON.stringify(payload,"  "))
        f.close()
    scene.queue_free()
    await process_frame
    print("R7_RAM_CAMERA_PROBE_V408 "+JSON.stringify({
      "status":payload["status"],"checks":count,"captures":photos.size(),
      "fidelity":payload["fidelity"],"error_count":errors.size()}))
    quit(0 if errors.is_empty() else 1)