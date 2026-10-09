extends SceneTree
func _initialize()->void: call_deferred("_run")
func _check(ok:bool,name:String,failed:Array)->void:
    if not ok: failed.append(name)
func _run()->void:
    var failed:Array=[]
    var packed=load("res://main.tscn")
    var scene=packed.instantiate(); root.add_child(scene)
    for _i in range(6): await process_frame
    var rm=scene.get_node("RoomManager")
    rm.call("load_room_at_portal","R1","spaview",false)
    for _i in range(8): await process_frame
    var room=rm.get("current_room")
    var e=room.find_child("SourceCharacter_Eugene",true,false)
    _check(e!=null,"eugene_spawn",failed)
    var d=e.get_node_or_null("SourceFrameDriverV217") if e else null
    var a=e.get_node_or_null("SourceAnimationAudio") if e else null
    _check(d!=null,"driver_bound",failed); _check(a!=null,"audio_node",failed)
    if d:
        _check(String(d.call("source_family"))=="REST","initial_rest",failed)
        _check(int(d.call("source_frame"))==0,"initial_frame_0",failed)
        _check(bool(d.call("request_family","ATTACK","REST",false)),"attack_request",failed)
        for _i in range(8): d.call("source_update")
        _check(int(d.call("source_frame"))==61,"advanced_through_60",failed)
        _check(bool(a.get("roar_fired_for_cycle")),"roar_frame_60",failed)
        _check(d.get("render_encoding_seconds_per_frame") > 0.0666 and d.get("render_encoding_seconds_per_frame") < 0.0667,"render_encoding_15fps",failed)
    _check(e.get("source_frame_driver")!=null if e else false,"controller_driver_binding",failed)
    var out={"schema":"openazrael.kg001.eugene_source_frame_runtime","version":217,"status":"PASS" if failed.is_empty() else "FAIL","checks":9,"failed":failed,"wall_clock_cadence":"HOLD_SOURCE_EVIDENCE","render_encoding_fps":15}
    print("OPENAZRAEL_EUGENE_SOURCE_FRAME_V217 "+JSON.stringify(out))
    scene.queue_free(); await process_frame; quit(0 if failed.is_empty() else 1)
