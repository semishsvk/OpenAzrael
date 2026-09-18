extends Area3D

var item_id := ""
var display_name := ""
var visual_node: Node3D

func interact() -> void:
    if item_id.is_empty() or DemoState.has(item_id):
        return
    DemoState.acquire(item_id)
    if is_instance_valid(visual_node):
        visual_node.visible = false
    print("Picked up: ", display_name if not display_name.is_empty() else item_id)
    queue_free()
