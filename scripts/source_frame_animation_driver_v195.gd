extends Node
class_name SourceFrameAnimationDriverV195

signal source_frame_observed(family: String, frame: int)
signal source_family_transitioned(from_family: String, to_family: String)

var render_player: AnimationPlayer = null
var render_encoding_seconds_per_frame := 0.0
var families: Dictionary = {}
var current_family := ""
var current_frame := -1
var queued_family := ""
var loop_current := false
var finished := true

func configure(
    player: AnimationPlayer,
    family_bounds: Dictionary,
    encoding_seconds_per_frame: float
) -> bool:
    if player == null or encoding_seconds_per_frame <= 0.0:
        return false
    var normalized := {}
    for key in family_bounds.keys():
        var family := String(key)
        var bounds = family_bounds[key]
        if not (bounds is Array) or bounds.size() != 2:
            return false
        var start := int(bounds[0])
        var end := int(bounds[1])
        if end < start:
            return false
        normalized[family] = [start, end]
    render_player = player
    families = normalized
    render_encoding_seconds_per_frame = encoding_seconds_per_frame
    current_family = ""
    current_frame = -1
    queued_family = ""
    loop_current = false
    finished = true
    return true

func request_family(family: String, next_family: String = "", loop_family: bool = false) -> bool:
    if render_player == null or not is_instance_valid(render_player):
        return false
    if not families.has(family):
        return false
    if not render_player.has_animation(StringName(family)):
        return false
    if not next_family.is_empty():
        if not families.has(next_family):
            return false
        if not render_player.has_animation(StringName(next_family)):
            return false
    current_family = family
    current_frame = int(families[family][0])
    queued_family = next_family
    loop_current = loop_family
    finished = false
    return true

func source_update() -> bool:
    if finished or current_family.is_empty():
        return false
    if not _render_current_pose():
        finished = true
        return false

    # v190 ordering: evaluate/render source frame, dispatch frame observers,
    # then advance the integer source-frame state.
    source_frame_observed.emit(current_family, current_frame)

    var bounds: Array = families[current_family]
    var end := int(bounds[1])
    if current_frame < end:
        current_frame += 1
        return true

    if not queued_family.is_empty():
        var previous := current_family
        current_family = queued_family
        queued_family = ""
        current_frame = int(families[current_family][0])
        loop_current = false
        source_family_transitioned.emit(previous, current_family)
        return true

    if loop_current:
        current_frame = int(bounds[0])
        return true

    finished = true
    return true

func _render_current_pose() -> bool:
    if render_player == null or not is_instance_valid(render_player):
        return false
    if not render_player.has_animation(StringName(current_family)):
        return false
    var bounds: Array = families[current_family]
    var start := int(bounds[0])
    var pose_time := float(current_frame - start) * render_encoding_seconds_per_frame
    render_player.assigned_animation = StringName(current_family)
    render_player.seek(pose_time, true)
    return true

func source_frame() -> int:
    return current_frame

func source_family() -> String:
    return current_family

func is_finished() -> bool:
    return finished
