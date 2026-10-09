extends SceneTree
# Deterministic Godot Niamh source-clips' world/local pose samples,
# not an equivalence claim with original runtime wall-clock.
var failed: Array[String] = []
var tests := 0

func check(name: String, passed: bool) -> void:
    tests += 1
    if not passed:
        failed.append(name)

func _initialize() -> void:
    call_deferred("_run")

func _run() -> void:
    var packed = load("res://main.tscn")
    check("main_scene",packed is PackedScene)
    if packed == null:
        _finish(null,{})
        return
    var scene = packed.instantiate()
    root.add_child(scene)
    await process_frame
    await process_frame
    var manager = scene.get_node("RoomManager")
    manager.load_room("R7",false)
    await process_frame
    manager._on_character_animation_requested({
        "character":"Niamh","family":"NOLOOP1",
        "target_object":"nibody",
        "source_required":true,"next_family":"REST"
    })
    var model = manager.current_room.find_child("SourceCharacter_Niamh",true,false)
    check("character_render_hierarchy",model!=null)
    if model==null:
        _finish(scene,{})
        return
    var animator = model.get_node_or_null("SourceCharacterAnimation") as AnimationPlayer
    var belly = model.get_node_or_null("NIBELLY") as Node3D
    check("source_animator_exists",animator!=null)
    check("source_NIBELLY_exists",belly!=null)
    if animator==null or belly==null:
        _finish(scene,{})
        return
    var clip = animator.get_animation(&"NOLOOP1")
    var rest = animator.get_animation(&"REST")
    check("noloop1_present",clip!=null)
    check("rest_present",rest!=null)
    if clip==null or rest==null:
        _finish(scene,{})
        return
    var expected_fps=15.0
    var end_time=14.0/expected_fps
    check("noloop1_duration_provisional_14_over_15",absf(clip.length-end_time)<0.0005)
    check("rest_duration_provisional_26_over_15",absf(rest.length-26.0/expected_fps)<0.0005)
    check("has_NIBELLY_tracks",clip.get_track_count()>0)
    var values: Array = []
    var source_root_origin = model.global_position
    animator.play(&"NOLOOP1")
    for i in range(15):
        var t=float(i)/expected_fps
        animator.seek(t,true)
        var row = {
            "source_frame":i,
            "source_calibration_seconds":t,
            "belly_local_y":belly.position.y,
            "belly_world_y":belly.global_position.y,
            "belly_global_origin":[belly.global_position.x,belly.global_position.y,belly.global_position.z]
        }
        values.append(row)
    var original_first=float(values[0]["belly_world_y"])
    var last=float(values[-1]["belly_world_y"])
    check("source_rise_magnitude_positive",last-original_first>30.0)
    check("source_15_unique_samples",values.size()==15)
    check("source_no_transform_nan",values.all(func(a):
        return is_finite(float(a["belly_world_y"]))))
    animator.play(&"REST")
    animator.seek(0.0,true)
    var rest_start_y: float = belly.global_position.y
    animator.seek(minf(rest.length*.5,rest.length),true)
    var rest_mid_y: float = belly.global_position.y
    check("rest_y_near_end_rise",absf(rest_start_y-last)<12.0)
    check("original_room_anchor",source_root_origin.distance_to(Vector3(-107.138,-34.5992,63.9427))<.5)
    var audit = {
        "schema":"openazrael.c8.niamh_source_temporal.v404",
        "godot_status":"PASS" if failed.is_empty() else "FAIL",
        "checks":tests,"failed":failed,
        "source_fps_provisional":expected_fps,
        "noloop1_length_seconds":clip.length,
        "rest_length_seconds":rest.length,
        "source_rise_y":last-original_first,
        "model_anchor":[source_root_origin.x,source_root_origin.y,source_root_origin.z],
        "rest_start_belly_world_y":rest_start_y,
        "rest_mid_belly_world_y":rest_mid_y,
        "samples":values,
        "original_runtime_time_fidelity":"HOLD_NEEDS_ACTIVATION_ALIGNED_CAMERA"
    }
    _finish(scene,audit)

func _finish(scene: Node, result: Dictionary) -> void:
    if scene!=null:
        scene.queue_free()
    await process_frame
    await process_frame
    if result.is_empty():
        result={"status":"FAIL","failed":failed,"checks":tests}
    else:
        result["status"]="PASS" if failed.is_empty() else "FAIL"
    var f=FileAccess.open("res://.tmp/niamh_source_temporal_v404.json",FileAccess.WRITE)
    if f:
        f.store_string(JSON.stringify(result,"  "))
        f.close()
    print("OPENAZRAEL_NIAMH_SOURCE_TEMPORAL_V404 "+JSON.stringify({
      "status":result["status"],"checks":tests,"failed":failed,
      "source_fps_provisional":result.get("source_fps_provisional",0),
      "source_rise_y":result.get("source_rise_y",0),
      "rest_start_y":result.get("rest_start_belly_world_y",0),
      "noloop1_length":result.get("noloop1_length_seconds",0)
    }))
    quit(0 if failed.is_empty() else 1)