extends Area3D

var door_visual: Node3D
var door_id := 1
var open_angle_degrees := 90.0
var opened := false

func _open_flag() -> String:
    return "R1Door%dOpen" % door_id

func _apply_open_instant() -> void:
    if opened or not is_instance_valid(door_visual):
        return
    door_visual.rotate_y(deg_to_rad(open_angle_degrees))
    opened = true

func sync_from_state() -> void:
    if DemoState.flag(_open_flag()):
        _apply_open_instant()

func interact() -> void:
    if opened or DemoState.flag(_open_flag()):
        return
    if door_id == 2:
        if not DemoState.has("well_key"):
            print(LocalizationManager.tr_key("interaction.r1.door_locked"))
            return
        # This recovered flag name is present in WORLD.DAT.
        DemoState.set_flag("FR1DoorUnlocked")
    DemoState.set_flag(_open_flag())
    LegacyEvents.run("R1_CORRIDOR_DOOR_OPEN")
    if not is_instance_valid(door_visual):
        return
    var target := door_visual.rotation.y + deg_to_rad(open_angle_degrees)
    var tw := create_tween()
    tw.set_trans(Tween.TRANS_SINE)
    tw.set_ease(Tween.EASE_IN_OUT)
    tw.tween_property(door_visual, "rotation:y", target, 0.75)
    opened = true
    print(LocalizationManager.tr_key("interaction.r1.door_opened", {"door_id": door_id}))

func interaction_cursor_id() -> String:
    if opened or DemoState.flag(_open_flag()):
        return "CANT"
    if door_id == 2 and not DemoState.has("well_key"):
        return "CANT"
    return "USE"
