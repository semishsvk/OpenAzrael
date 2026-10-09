class_name AudioParityCaptureV71
extends RefCounted

const SCHEMA := "openazrael.audio_runtime_parity_capture"
const VERSION := 71

static func build_record(room_id: String, mode_name: String, listener_position: Vector3, listener_forward: Vector3, snapshots: Array[Dictionary], master_volume: int) -> Dictionary:
    var emitters: Array[Dictionary] = []
    for s in snapshots:
        var p: Dictionary = s.get("classic_parity_v68", {})
        emitters.append({
            "legacy_3d_slot": int(s.get("legacy_3d_slot", -1)),
            "node": String(s.get("node", "")),
            "sample_source": String(s.get("source", "")),
            "legacy_position": s.get("legacy_position", []),
            "openazrael_reference": p,
            "original_observation": {
                "status": "UNOBSERVED",
                "pan": null,
                "volume": null,
                "capture_method": null,
                "notes": "Populate only from an independently observed/instrumented original-demo run."
            }
        })
    emitters.sort_custom(func(a: Dictionary, b: Dictionary): return int(a["legacy_3d_slot"]) < int(b["legacy_3d_slot"]))
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "room_id": room_id,
        "audio_mode": mode_name,
        "parity_master_volume": master_volume,
        "listener": {
            "position": [listener_position.x, listener_position.y, listener_position.z],
            "forward": [listener_forward.x, listener_forward.y, listener_forward.z]
        },
        "emitters": emitters,
        "confidence": {
            "demo_coordinate_transform": "HIGH_V67",
            "heading_model": "HIGH_V65",
            "angle_constant_semantics": "HIGH_V70",
            "placeholder_to_literal_le_relocation": "PROVISIONAL",
            "playback_mutation": false
        }
    }

static func append_jsonl(path: String, record: Dictionary) -> Error:
    var f := FileAccess.open(path, FileAccess.READ_WRITE)
    if f == null:
        f = FileAccess.open(path, FileAccess.WRITE)
    if f == null:
        return FileAccess.get_open_error()
    f.seek_end()
    f.store_line(JSON.stringify(record))
    f.close()
    return OK
