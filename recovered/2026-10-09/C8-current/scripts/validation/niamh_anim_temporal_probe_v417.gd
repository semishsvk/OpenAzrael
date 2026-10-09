extends SceneTree
## OpenAzrael C8 v417:
## Actual Godot source Niamh NOLOOP1 at 15 authored frames,
## with registered ORIGINAL R7 player camera. Pose/timing comparison
## is experiment-only; no gameplay code, source animation, or GDScript
## production shader/material modification.
const EYE := Vector3(7.648277282714844,4.2041473388671875,3.9145851135253906)
const LOOK := Vector3(-0.9135454297065735,0,0.4067366421222687)
var checks := 0
var failures: Array[String] = []
var evidence: Array[Dictionary] = []
var sha := HashingContext.new()

func ck(label: String, result: bool) -> void:
    checks += 1
    if not result:
        failures.append(label)

func _initialize() -> void:
    call_deferred("_run")

func _save(label: String, ap: AnimationPlayer, mid: Node3D) -> void:
    await process_frame
    await RenderingServer.frame_post_draw
    var original_img: Image = root.get_viewport().get_texture().get_image()
    original_img.convert(Image.FORMAT_RGB8)
    ck("source_640x480_"+label,original_img.get_size()==Vector2i(640,480))
    var filename="res://.tmp/niamh_animation_source_v417_"+label+".png"
    var code=original_img.save_png(filename)
    ck("png_export_"+label,code==OK)
    var ctx=HashingContext.new()
    ctx.start(HashingContext.HASH_SHA256)
    ctx.update(original_img.get_data())
    var rgb_sha=ctx.finish().hex_encode()
    var y=mid.global_position.y
    evidence.append({"id":label,"source_anim_time":ap.current_animation_position,
       "belly_source_world_Y":y,"pixel_rgb_sha256":rgb_sha,
       "png_path":filename})

func _run() -> void:
    root.get_window().size=Vector2i(640,480)
    var state=root.get_node("DemoState")
    state.reset_all()
    state.set_flag("R7NiamhActivated",true)
    var packed=load("res://main.tscn") as PackedScene
    ck("source_demo_main",packed!=null)
    if packed==null:
        _done(null)
        return
    var main=packed.instantiate()
    root.add_child(main)
    await process_frame
    await process_frame
    for obj in main.get_children():
        if obj is CanvasLayer:
            obj.visible=false
    var manager=main.get_node("RoomManager")
    manager.transition_cooldown=999.0
    manager.load_room("R7",false)
    await process_frame
    var player=main.get_node("Player") as CharacterBody3D
    player.set_process(false)
    player.set_physics_process(false)
    player.teleport_eye_to(EYE,LOOK)
    player._apply_source_projection()
    var cam=player.get_node("Camera3D") as Camera3D
    ck("source_camera_negative_x",cam.global_basis.determinant()<0)
    ck("source_camera_position",cam.global_position.distance_to(EYE)<.001)
    ck("source_camera_forward",(-cam.global_basis.z).distance_to(LOOK)<.001)
    await _save("background",AnimationPlayer.new(),manager.current_room)
    manager._on_character_animation_requested({
      "character":"Niamh","family":"NOLOOP1","target_object":"nibody",
      "source_required":true,"next_family":"REST"})
    var model=manager.current_room.find_child("SourceCharacter_Niamh",true,false) as Node3D
    ck("source_niamh_model",model!=null)
    if model==null:
        _done(main)
        return
    var ap=model.get_node_or_null("SourceCharacterAnimation") as AnimationPlayer
    var belly=model.find_child("NIBELLY",true,false) as Node3D
    ck("source_animator",ap!=null)
    ck("source_belly",belly!=null)
    if ap==null or belly==null:
        _done(main)
        return
    ck("v415_position_over_original_well",model.global_position.distance_to(Vector3(-99.226,5.4008,38.004))<.5)
    ck("v415_yaw90",absf(model.rotation.y-deg_to_rad(90))<.01)
    ck("source_NOLOOP1_present",ap.has_animation(&"NOLOOP1"))
    var clip=ap.get_animation(&"NOLOOP1")
    ck("no_loop_length_14_frames_at15fps",absf(clip.length-14.0/15.0)<.0005)
    ap.play(&"NOLOOP1")
    ap.pause()
    for i in range(15):
        var t=float(i)/15.0
        ap.seek(t,true)
        await _save("frame_"+str(i).pad_zeros(2),ap,belly)
    ck("fifteen_source_frames",evidence.size()==16)
    var root0: float=float(evidence[1]["belly_source_world_Y"])
    var root14: float=float(evidence[-1]["belly_source_world_Y"])
    ck("authored_niamh_rise_gt70",root14-root0>70.0)
    ap.play(&"REST")
    ap.pause()
    ap.seek(0.0,true)
    await _save("rest",ap,belly)
    var report={"schema":"openazrael.c8.Niamh_source_camera_animation_samples.v417",
      "status":"PASS" if failures.is_empty() else "FAIL",
      "checks":checks,"failures":failures,
      "camera":"ORIGINAL_RAM_PRODUCTION_PLAYER_CAMERA",
      "source_animation":"NIAMH.ANI NOLOOP1/REST",
      "source_fps_hypothesis":15.0,
      "original_source_R_EXE_sha256":"381e4f5c61e4bb8c27f06b1944e6673bbebc39ca219cc08fb9f948da2ca37c00",
      "NIAMH_XAF_sha256":"6208e8831aa196b328b1c0f526765955e3eb0816e4a706f5c6c337c6c2708692",
      "captures":evidence,
      "source_belly_rise":root14-root0,
      "original_game_NIAMH_rise_time":"HOLD",
      "godot_candidate_fidelity":"HOLD"}
    var f=FileAccess.open("res://.tmp/niamh_animation_source_samples_v417.json",FileAccess.WRITE)
    if f:
        f.store_string(JSON.stringify(report,"  "))
        f.close()
    _done(main)

func _done(main: Node) -> void:
    if main!=null:
        main.queue_free()
    await process_frame
    print("NIAMH_ANIMATION_SAMPLES_V417 "+JSON.stringify({
      "status":"PASS" if failures.is_empty() else "FAIL",
      "checks":checks,"failures":failures,
      "source_frames":evidence.size(),
      "original_visual_fidelity":"HOLD"}))
    quit(0 if failures.is_empty() else 1)