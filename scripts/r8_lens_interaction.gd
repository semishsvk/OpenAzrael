extends Area3D

var lens_visual: Node3D

func interact() -> void:
    if DemoState.has("r8_lens"):
        return
    if not DemoState.flag("R8BathDrain"):
        print("The lens is still beneath the murky bath water. The Well Room pipe puzzle must drain it first.")
        return
    DemoState.acquire("r8_lens")
    DemoState.set_flag("R8Lens")
    if is_instance_valid(lens_visual):
        lens_visual.visible = false
    print("Retrieved the lens from the drained bath.")
    queue_free()
