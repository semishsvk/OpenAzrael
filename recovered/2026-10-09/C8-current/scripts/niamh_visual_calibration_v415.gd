extends RefCounted
## Candidate 8, Demo R7 only: visual placement measured from six
## authentic original R.EXE/ATI DEMO DOSBox-X frames.
## NEVER interpreted as an authored NIAMH.ANI OFFSET or universal XAF rule.
## Normal source room character transforms remain the fallback if this
## explicit bounded visual contract is missing or fails any check.

const CONTRACT := "res://data/reconstruction/niamh_visual_calibration_v415.json"
const ORIGINAL_R_EXE := "381e4f5c61e4bb8c27f06b1944e6673bbebc39ca219cc08fb9f948da2ca37c00"
const ORIGINAL_NIAMH_XAF := "6208e8831aa196b328b1c0f526765955e3eb0816e4a706f5c6c337c6c2708692"

static func apply(character_root: Node3D, authored_proxy: Node3D, room: Node3D) -> Dictionary:
    if character_root == null or authored_proxy == null or room == null:
        return {"status":"HOLD_VISUAL_CALIBRATION_MISSING_OBJECT"}
    if not FileAccess.file_exists(CONTRACT):
        return {"status":"HOLD_VISUAL_CALIBRATION_MISSING_CONTRACT"}
    var raw = JSON.parse_string(FileAccess.get_file_as_string(CONTRACT))
    if not raw is Dictionary or int(raw.get("version",-1)) != 415 or str(raw.get("schema","")) != "openazrael.c8.niamh_original_frame_calibration.v415":
        return {"status":"HOLD_VISUAL_CALIBRATION_INVALID_SCHEMA"}
    if str(raw.get("project_scope","")) != "OpenAzrael Demo C8 R7 only; NOT Retail and NOT universal framework":
        return {"status":"HOLD_VISUAL_CALIBRATION_SCOPE"}
    var provenance = raw.get("source_authority",{})
    var measured = raw.get("measured_transform",{})
    if not provenance is Dictionary or not measured is Dictionary:
        return {"status":"HOLD_VISUAL_CALIBRATION_MISSING_PROVENANCE"}
    if str(provenance.get("read_only_original_R_EXE_SHA256","")) != ORIGINAL_R_EXE or str(provenance.get("NIAMH_XAF_SHA256","")) != ORIGINAL_NIAMH_XAF:
        return {"status":"HOLD_VISUAL_CALIBRATION_WRONG_SOURCE"}
    if str(provenance.get("room","")) != "R7" or str(provenance.get("source_actor_proxy","")) != "nibody" or str(provenance.get("well_source_object","")) != "wel_well__WELL_WELLWALL":
        return {"status":"HOLD_VISUAL_CALIBRATION_WRONG_OBJECT"}
    if str(measured.get("depth_policy","")) != "SOURCE_OPAQUE_WITH_STANDARD_DEPTH_TEST" or str(measured.get("transparency_override","")) != "NONE":
        return {"status":"HOLD_VISUAL_CALIBRATION_MATERIAL_POLICY"}
    if not measured.get("NIAMH_ANI_HEIGHT33_IS_NOT_TREATED_AS_TRANSLATION",false):
        return {"status":"HOLD_VISUAL_CALIBRATION_SOURCE_SEMANTIC_INVARIANT"}
    var height = float(measured.get("vertical_offset",-10000))
    var heading = float(measured.get("yaw_degrees",-10000))
    if not is_finite(height) or not is_finite(heading) or absf(height-40.0)>.0001 or absf(heading-90.0)>.0001:
        return {"status":"HOLD_VISUAL_CALIBRATION_UNTESTED_PARAMETER"}
    var evidence = raw.get("source_native_capture_evidence",[])
    if not evidence is Array or evidence.size()!=6:
        return {"status":"HOLD_VISUAL_CALIBRATION_NO_ORIGINAL_FRAMES"}
    var well = room.find_child("wel_well__WELL_WELLWALL",true,false) as Node3D
    if well == null:
        return {"status":"HOLD_VISUAL_CALIBRATION_WELL_REFERENCE_MISSING"}
    var expected = Vector3(-99.226,-36.486,38.004)
    if well.global_position.distance_to(expected) > .20:
        return {"status":"HOLD_VISUAL_CALIBRATION_SOURCE_WORLD_MOVED"}
    var source = authored_proxy.global_position
    if source.distance_to(Vector3(-107.138,-34.5992,63.9427)) > .20:
        return {"status":"HOLD_VISUAL_CALIBRATION_PROXY_SOURCE_DRIFT"}
    # The 40-unit upward position is an empirical screenshot fit, not the
    # NIAMH.ANI HEIGHT metadata. Keep source geometry and animation intact.
    character_root.global_position=Vector3(well.global_position.x,source.y+height,well.global_position.z)
    character_root.rotate_y(deg_to_rad(heading))
    return {
        "status":"APPLIED_ORIGINAL_FRAME_CALIBRATION_PROVISIONAL",
        "room":"R7","source_actor_proxy":"nibody",
        "position":[character_root.global_position.x,character_root.global_position.y,character_root.global_position.z],
        "yaw_deg":heading,"depth_policy":"OPAQUE_DEPTH_TEST",
        "original_source_frame_count":evidence.size(),
        "candidate_fidelity":"HOLD"
    }
