extends SceneTree
## Bound original-runtime visual-fit check for DEMO R7 only.
## Checks rendering placement/material invariants, NOT final frame fidelity.
const Fit = preload("res://scripts/niamh_visual_calibration_v415.gd")
var failures: Array[String]=[]
var checks:=0
var reports: Array[Dictionary]=[]

func ck(name: String, ok: bool) -> void:
    checks+=1
    if not ok:
        failures.append(name)

func _record(row: Dictionary) -> void:
    if String(row.get("kind",""))=="niamh_visual_calibration":
        var data=row.get("data",{})
        if data is Dictionary:
            reports.append(data.duplicate(true))

func _initialize()->void:
    call_deferred("_run")

func _find_meshes(n: Node, result: Array[MeshInstance3D])->void:
    if n is MeshInstance3D:
        result.append(n as MeshInstance3D)
    for child in n.get_children():
        _find_meshes(child,result)

func _run()->void:
    var diagnostics=root.get_node("CandidateDiagnostics")
    var state=root.get_node("DemoState")
    diagnostics.event_recorded.connect(_record)
    state.reset_all()
    var main=(load("res://main.tscn") as PackedScene).instantiate()
    root.add_child(main)
    await process_frame
    await process_frame
    var room=main.get_node("RoomManager")
    room.load_room("R7",false)
    await process_frame
    var target=room.current_room.find_child("nibody",true,false) as Node3D
    var well=room.current_room.find_child("wel_well__WELL_WELLWALL",true,false) as Node3D
    ck("authored_R7_nibody_proxy",target!=null)
    ck("authored_R7_source_well_pivot",well!=null)
    if target==null or well==null:
        _finish(main)
        return
    ck("original_well_pivot_unchanged",well.global_position.distance_to(Vector3(-99.226,-36.486,38.004))<.2)
    ck("source_actor_proxy_unchanged",target.global_position.distance_to(Vector3(-107.138,-34.5992,63.9427))<.2)
    room._on_character_animation_requested({
        "character":"Niamh","family":"NOLOOP1",
        "target_object":"nibody","source_required":true,"next_family":"REST"
    })
    var model=room.current_room.find_child("SourceCharacter_Niamh",true,false) as Node3D
    ck("character_source_GLB_spawned",model!=null)
    if model==null:
        _finish(main)
        return
    var expected=Vector3(well.global_position.x,target.global_position.y+40.0,well.global_position.z)
    ck("measured_visual_center_over_source_well",model.global_position.distance_to(expected)<.01)
    ck("calibrated_yaw90",absf(wrapf(model.rotation.y-deg_to_rad(90),-PI,PI))<.01)
    ck("source_movement_family_playing",String(room.character_animation_status("Niamh").get("family",""))=="NOLOOP1")
    ck("recorded_single_visual_calibration",reports.size()==1)
    if not reports.is_empty():
        ck("provenance_status_scoped",reports[0].get("status")=="APPLIED_ORIGINAL_FRAME_CALIBRATION_PROVISIONAL")
        ck("visual_not_claimed_final",reports[0].get("candidate_fidelity")=="HOLD")
    var meshes: Array[MeshInstance3D]=[]
    _find_meshes(model,meshes)
    ck("authored_source_mesh_count19",meshes.size()==19)
    var visible_material_count:=0
    for mesh in meshes:
        if mesh.mesh==null:
            continue
        for idx in range(mesh.mesh.get_surface_count()):
            var material=mesh.get_active_material(idx) as BaseMaterial3D
            if material!=null:
                visible_material_count+=1
                ck("source_mesh_opaque_"+str(visible_material_count),material.transparency==BaseMaterial3D.TRANSPARENCY_DISABLED)
                ck("source_mesh_uses_depth_"+str(visible_material_count),not material.no_depth_test)
    ck("source_19_materials",visible_material_count==19)
    # Fail closed: deliberately wrong room reference must leave a valid
    # already calibrated model untouched and report HOLD.
    var dummy=Node3D.new()
    room.current_room.add_child(dummy)
    var before=model.global_position
    var invalid=Fit.apply(model,target,dummy)
    ck("invalid_well_fails_closed",String(invalid.get("status",""))=="HOLD_VISUAL_CALIBRATION_WELL_REFERENCE_MISSING")
    ck("invalid_well_does_not_mutate_model",model.global_position.distance_to(before)<.0001)
    dummy.queue_free()
    state.reset_all()
    _finish(main)

func _finish(main: Node)->void:
    if main!=null:
        main.queue_free()
    await process_frame
    await process_frame
    var status="PASS" if failures.is_empty() else "FAIL"
    var data={"schema":"openazrael.c8.niamh_source_registered_visual_runtime.v415",
      "status":status,"checks":checks,"failed":failures,
      "source_R7_well":"wel_well__WELL_WELLWALL",
      "native_original_frame_calibration":true,"original_render_fidelity":"HOLD"}
    var file=FileAccess.open("res://.tmp/niamh_visual_runtime_v415.json",FileAccess.WRITE)
    if file:
        file.store_string(JSON.stringify(data,"  "))
        file.close()
    print("OPENAZRAEL_NIAMH_VISUAL_V415 "+JSON.stringify(data))
    quit(0 if failures.is_empty() else 1)