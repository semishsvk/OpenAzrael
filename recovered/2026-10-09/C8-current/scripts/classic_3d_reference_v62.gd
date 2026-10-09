class_name Classic3DReferenceV62
extends RefCounted

# Safe forensic reference after the v62 adversarial heading audit.
# XYZ -> heading is intentionally NOT exposed until 0x30D7A is closed correctly.
const DISTANCE_NUMERATOR := 15000.0
const GAIN_CEILING := 99
const PAN_SPAN := 63.0
const PAN_CENTER := 64.0

static func pan_from_verified_headings(listener_deg: float, source_deg: float) -> Dictionary:
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
