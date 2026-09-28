extends Area3D

var tapestry_visual: Node3D
var message_visual: Node3D
var rotated := false

func sync_from_state() -> void:
    if DemoState.puzzle_node("R8TapestryBack") and not rotated:
        _rotate_instant()

func _rotate_instant() -> void:
    if is_instance_valid(tapestry_visual):
        # Source XAF evidence: tapestry2a is the hidden back face and its
        # authored BAPMSG UV is vertically reversed relative to tapestry2.
        # A 180-degree rotation around the horizontal X axis both reveals the
        # back face and restores the message's intended upright world
        # orientation. A Y-axis turn reveals the back but leaves the readable
        # message upside down.
        tapestry_visual.rotate_x(PI)
    if is_instance_valid(message_visual):
        message_visual.visible = true
    rotated = true

func interact() -> void:
    if rotated or DemoState.puzzle_node("R8TapestryBack"):
        return
    DemoState.set_flag("R8TapestryRotate")
    DemoState.set_puzzle_node("R8TapestryBack")
    if is_instance_valid(message_visual):
        message_visual.visible = true
    if is_instance_valid(tapestry_visual):
        var tw := create_tween()
        tw.set_trans(Tween.TRANS_SINE)
        tw.set_ease(Tween.EASE_IN_OUT)
        tw.tween_property(tapestry_visual, "rotation:x", tapestry_visual.rotation.x + PI, 0.8)
    rotated = true
    print("Rotated the hanging tapestry to reveal its message.")

func interaction_cursor_id() -> String:
    return "CANT" if rotated or DemoState.puzzle_node("R8TapestryBack") else "ROT"
