extends SceneTree
# Candidate 8 camera registration probe using the ORIGINAL R.EXE DOSBox-X
# save-memory player/camera transform at 0x35B5E0/0x35B864.
# R7 original native framebuffer central 3D window is approx 552x280.
# Different vertical FOV options remain HYPOTHESES until capture comparison.
const NATIVE_ORIGINAL_EYE := Vector3(0.0,-69.44447326660156,0.0)
const NATIVE_FORWARD := Vector3(0,0,1)
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
    var filename="res://.tmp/r1_native_camera_v409_"+name+".png"
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
    m.load_room("R1",false)
    await process_frame
    var camera=Camera3D.new()
    camera.name="R1_ORIGINAL_RAM_CAMERA_V409"
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
    var payload={"schema":"openazrael.c8.original_r1_camera_fov_probe.v409",
     "status":"PASS" if errors.is_empty() else "FAIL",
     "checks":count,"failed":errors,
     "original_memory_eye_xyz":[NATIVE_ORIGINAL_EYE.x,NATIVE_ORIGINAL_EYE.y,NATIVE_ORIGINAL_EYE.z],
     "original_memory_look_unit":[NATIVE_FORWARD.x,NATIVE_FORWARD.y,NATIVE_FORWARD.z],
     "source_save_sha256":"a9489051015ad06aadf68fa022ef200bd90001b707b8cd12324cea28c85eef76",
     "engine":"Godot 4.7.2 GL compatibility",
     "camera_fov_candidates":[35,45,55,65,75,85,95,105],
     "framing":"552x280 original R1 3D window crop",
     "captures":photos,
     "fidelity":"HOLD_UNTIL_DIRECT_ORIGINAL_PERSPECTIVE_DIFF"}
    var f=FileAccess.open("res://.tmp/r1_camera_registration_probe_v409.json",FileAccess.WRITE)
    if f:
        f.store_string(JSON.stringify(payload,"  "))
        f.close()
    scene.queue_free()
    await process_frame
    print("R1_RAM_CAMERA_PROBE_V409 "+JSON.stringify({
      "status":payload["status"],"checks":count,"captures":photos.size(),
      "fidelity":payload["fidelity"],"error_count":errors.size()}))
    quit(0 if errors.is_empty() else 1)