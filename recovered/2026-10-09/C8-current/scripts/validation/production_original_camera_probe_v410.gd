extends SceneTree
# Production Player/Camera3D parity probe against original player state.
# Source retained-mode handedness is already encoded in main.tscn and player.gd.
# This script changes NO production renderer code and uses the real Player camera.
const R1_EYE:=Vector3(0,-69.44447326660156,0)
const R1_FWD:=Vector3(0,0,1)
const R7_EYE:=Vector3(7.648277282714844,4.2041473388671875,3.9145851135253906)
const R7_FWD:=Vector3(-0.9135454297065735,0,0.4067366421222687)
var failures:Array[String]=[]
var checks:=0
var images:Array[Dictionary]=[]
var observed:Array[Dictionary]=[]

func test(name:String,ok:bool)->void:
    checks+=1
    if not ok:
        failures.append(name)
func _initialize()->void:
    call_deferred("_run")

func _capture(label:String,camera:Camera3D,expected:Vector3,expected_forward:Vector3)->void:
    await process_frame
    await RenderingServer.frame_post_draw
    var pos=camera.global_position
    var direct=-camera.global_basis.z
    test("eye_"+label,pos.distance_to(expected)<.002)
    test("forward_"+label,direct.distance_to(expected_forward)<.002)
    test("negative_x_handedness_"+label,camera.global_basis.determinant()<0)
    test("source_frustum_active_"+label,camera.projection==Camera3D.PROJECTION_FRUSTUM)
    var screenshot=root.get_viewport().get_texture().get_image()
    screenshot.convert(Image.FORMAT_RGB8)
    var path="res://.tmp/original_player_camera_v410_"+label+".png"
    var saved=screenshot.save_png(path)
    test("save_"+label,saved==OK and screenshot.get_size()==Vector2i(640,480))
    images.append({"label":label,"path":path,"width":screenshot.get_width(),"height":screenshot.get_height()})
    observed.append({"label":label,
      "eye":[pos.x,pos.y,pos.z],
      "forward":[direct.x,direct.y,direct.z],
      "basis_determinant":camera.global_basis.determinant(),
      "projection":int(camera.projection),
      "frustum_offset":[camera.frustum_offset.x,camera.frustum_offset.y],
      "frustum_size":camera.size,"near":camera.near,"far":camera.far})

func _run()->void:
    root.get_window().size=Vector2i(640,480)
    var main=(load("res://main.tscn") as PackedScene).instantiate()
    root.add_child(main)
    await process_frame
    await process_frame
    for n in main.get_children():
        if n is CanvasLayer:
            n.visible=false
    var manager=main.get_node("RoomManager")
    var player=main.get_node("Player") as CharacterBody3D
    var cam=player.get_node("Camera3D") as Camera3D
    test("production_camera_exists",cam!=null)
    player.set_process(false)
    player.set_physics_process(false)
    manager.transition_cooldown=999.0
    player.teleport_eye_to(R1_EYE,R1_FWD)
    player._apply_source_projection()
    await _capture("R1",cam,R1_EYE,R1_FWD)
    # After original one-shot Niamh is already active; hide source proxy
    # explicitly so environment geometry can be compared independent of actor.
    var state=root.get_node("DemoState")
    state.set_flag("R7NiamhActivated",true)
    manager.load_room("R7",false)
    manager.transition_cooldown=999.0
    player.teleport_eye_to(R7_EYE,R7_FWD)
    player._apply_source_projection()
    var proxy=manager._find_node("nibody") as Node3D
    if proxy!=null:
        proxy.visible=false
    await _capture("R7_BACKGROUND",cam,R7_EYE,R7_FWD)
    manager._on_character_animation_requested({
      "character":"Niamh","family":"NOLOOP1",
      "target_object":"nibody","source_required":true,
      "next_family":"REST"})
    var model=manager.current_room.find_child("SourceCharacter_Niamh",true,false)
    test("source_character_exists",model!=null)
    if model!=null:
        var ap=model.get_node("SourceCharacterAnimation") as AnimationPlayer
        ap.play(&"REST")
        ap.seek(0.0,true)
        await _capture("R7_NIAMH_REST",cam,R7_EYE,R7_FWD)
    var report={"schema":"openazrael.c8.production_camera_original_RAM.v410",
      "status":"PASS" if failures.is_empty() else "FAIL",
      "checks":checks,"failed":failures,"captures":images,
      "camera_from_original_memory":observed,
      "world_engine":"SOURCE_PLAYER_CAM_MAIN_TSCN",
      "original_r1_save_sha256":"a9489051015ad06aadf68fa022ef200bd90001b707b8cd12324cea28c85eef76",
      "original_r7_save_sha256":"7694f3c2edef8b47599b295624e751cd218ae53aadd9fe403aedcf28505ba650",
      "candidate_fidelity":"HOLD_NOT_YET_PIXEL_COMPARISON"}
    var f=FileAccess.open("res://.tmp/production_camera_original_ram_v410.json",FileAccess.WRITE)
    if f:
        f.store_string(JSON.stringify(report,"  "))
        f.close()
    main.queue_free()
    await process_frame
    print("OPENAZRAEL_PRODUCTION_CAMERA_V410 "+JSON.stringify({
      "status":report["status"],"checks":checks,"failed":failures,"captures":images.size(),
      "handedness_reflection_already_present":true}))
    quit(0 if failures.is_empty() else 1)