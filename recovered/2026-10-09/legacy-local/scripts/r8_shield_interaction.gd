extends Area3D

var shield_visual: Node3D

func interact() -> void:
    if not DemoState.puzzle_node("DoorR8"):
        print(LocalizationManager.tr_key("interaction.r8.shield_blocked"))
        return
    if DemoState.flag("demo_complete"):
        return
    LegacyEvents.run("R8_TAKE_SHIELD")
    if is_instance_valid(shield_visual):
        shield_visual.visible = false
    print(LocalizationManager.tr_key("interaction.r8.shield_acquired"))
    queue_free()

func interaction_cursor_id() -> String:
    if not DemoState.puzzle_node("DoorR8") or DemoState.flag("demo_complete"):
        return "CANT"
    return "TAKE"
