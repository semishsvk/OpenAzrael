class_name AudioDebugViewV69
extends RefCounted

static func format_snapshot(room_id: String, mode_name: String, snapshots: Array[Dictionary], master_volume: int) -> String:
    var lines: Array[String] = []
    lines.append("AUDIO DEBUG v69  [F8 close]")
    lines.append("Room %s | mode %s | parity master %d" % [room_id, mode_name, master_volume])
    lines.append("Classic shadow: V65 heading HIGH | caller constants PROVISIONAL")
    lines.append("Demo coordinates: identity HIGH | playback remains Godot approximate")
    if snapshots.is_empty():
        lines.append("No legacy ambient emitters in current room")
        return "\n".join(lines)
    var ordered := snapshots.duplicate()
    ordered.sort_custom(func(a: Dictionary, b: Dictionary): return int(a.get("legacy_3d_slot", 99)) < int(b.get("legacy_3d_slot", 99)))
    for s in ordered:
        var p: Dictionary = s.get("classic_parity_v68", {})
        var legacy = s.get("legacy_position", [])
        var xyz := "?"
        if legacy is Array and legacy.size() >= 3:
            xyz = "(%g,%g,%g)" % [float(legacy[0]), float(legacy[1]), float(legacy[2])]
        if p.get("status", "") == "HOLD_ZERO_HORIZONTAL_VECTOR":
            lines.append("S%d %-18s xyz=%s d=%.2f  HOLD zero horizontal" % [int(s.get("legacy_3d_slot", -1)), String(s.get("node", "?")), xyz, float(p.get("distance", 0.0))])
            continue
        lines.append("S%d %-18s xyz=%s" % [int(s.get("legacy_3d_slot", -1)), String(s.get("node", "?")), xyz])
        lines.append("   d=%7.2f  L=%6.1f° S=%6.1f° fold=%6.1f°  pan=%3d rear=/ %d  vol=%3d" % [
            float(p.get("distance", 0.0)), float(p.get("listener_heading_deg", 0.0)), float(p.get("source_heading_deg", 0.0)),
            float(p.get("folded_angle_deg", 0.0)), int(p.get("pan", -1)), int(p.get("rear_mode_divisor", -1)), int(p.get("volume", -1))])
    return "\n".join(lines)
