class_name Classic3DReferenceV61
extends RefCounted

# Forensic reference only; not yet wired into the live AudioStreamPlayer3D renderer.
const DISTANCE_NUMERATOR := 15000.0
const GAIN_CEILING := 99
const PAN_SPAN := 63.0
const PAN_CENTER := 64.0

static func heading_from_xz(v: Vector3) -> float:
    var h := Vector2(v.x, v.z)
    if h.length_squared() == 0.0:
        return NAN # original zero-vector normalization behavior remains HOLD
    h = h.normalized()
    var angle := rad_to_deg(asin(clamp(h.y, -1.0, 1.0)))
    if h.x > 0.0:
        angle = 360.0 - angle
    return angle

static func pan_from_headings(listener_deg: float, source_deg: float) -> Dictionary:
    var d: float
    var mode := 1
    if listener_deg <= 180.0 and source_deg > 180.0:
        d = 360.0 - source_deg + listener_deg
        if d > 180.0:
            d = -(360.0 - d)
    else:
        d = -(360.0 - listener_deg + source_deg)
        if d < -180.0:
            d += 360.0
    if d > 90.0:
        mode = 2
        d = 180.0 - d
    elif d < -90.0:
        mode = 2
        d = -180.0 - d
    return {"pan": int(d * PAN_SPAN / 90.0 + PAN_CENTER), "folded_angle_deg": d, "mode_divisor": mode}

static func attenuation(distance: float, master_volume: int, mode_divisor: int = 1) -> int:
    var raw := GAIN_CEILING if distance == 0.0 else int(DISTANCE_NUMERATOR / distance)
    var gain: int = min(int(raw / mode_divisor), GAIN_CEILING)
    return int(master_volume * gain / GAIN_CEILING)
