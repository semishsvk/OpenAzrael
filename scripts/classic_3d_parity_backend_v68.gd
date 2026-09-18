class_name Classic3DParityBackendV68
extends RefCounted

# Parallel forensic backend. It computes the reconstructed Miles-era values but
# intentionally does not drive Godot playback until the remaining caller
# constant bindings are independently closed.
const Ref := preload("res://scripts/classic_3d_reference_v65.gd")
const Coord := preload("res://scripts/azrael_coordinate_transform.gd")

static func evaluate(listener_position: Vector3, listener_forward: Vector3, source_position: Vector3, master_volume: int = 99) -> Dictionary:
    var lp := Coord.legacy_to_godot_position(listener_position)
    var sp := Coord.legacy_to_godot_position(source_position)
    var lf := Coord.legacy_to_godot_direction(listener_forward)
    var source_delta := sp - lp
    var lh = Ref.heading_from_xz(lf.x, lf.z)
    var sh = Ref.heading_from_xz(source_delta.x, source_delta.z)
    if lh == null or sh == null:
        return {
            "status": "HOLD_ZERO_HORIZONTAL_VECTOR",
            "distance": source_delta.length(),
            "pan": null,
            "rear_mode_divisor": null,
            "volume": null
        }
    var pan_result := Ref.pan_from_headings(float(lh), float(sh))
    var distance := source_delta.length()
    var divisor := int(pan_result["mode_divisor"])
    var volume := Ref.attenuation(distance, master_volume, divisor)
    return {
        "status": "REFERENCE_V68",
        "distance": distance,
        "listener_heading_deg": float(lh),
        "source_heading_deg": float(sh),
        "folded_angle_deg": float(pan_result["folded_angle_deg"]),
        "pan": int(pan_result["pan"]),
        "rear_mode_divisor": divisor,
        "volume": volume,
        "master_volume": master_volume,
        "coordinate_transform_confidence": Coord.confidence(),
        "heading_confidence": "HIGH_V65",
        "caller_angle_constant_binding": "PROVISIONAL_V64"
    }
