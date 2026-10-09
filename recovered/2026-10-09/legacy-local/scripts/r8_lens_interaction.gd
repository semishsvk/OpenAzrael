extends Area3D

var lens_visual: Node3D

func interact() -> void:
    if DemoState.has("r8_lens"):
        return
    if not DemoState.flag("R8BathDrain"):
        print(LocalizationManager.tr_key("interaction.r8.lens_submerged"))
        return
    DemoState.acquire("r8_lens")
    DemoState.set_flag("R8Lens")
    if is_instance_valid(lens_visual):
        lens_visual.visible = false
    print(LocalizationManager.tr_key("interaction.r8.lens_retrieved"))
    queue_free()

func interaction_cursor_id() -> String:
    if DemoState.has("r8_lens"):
        return "CANT"
    return "TAKE" if DemoState.flag("R8BathDrain") else "CANT"
