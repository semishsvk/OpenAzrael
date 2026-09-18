extends Area3D

var key_visual: Node3D

func interact() -> void:
    if DemoState.has("well_key"):
        return
    if not DemoState.has("rusty_tongs"):
        print("The key is out of reach. The demo requires the tongs.")
        return
    if DemoState.retrieve_well_key():
        if is_instance_valid(key_visual):
            key_visual.visible = false
        print("Retrieved the Well Key with the tongs.")
        queue_free()
