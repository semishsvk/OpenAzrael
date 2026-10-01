extends Area3D
## Source-backed adapter for original carried-object + book action groups.
const BookPresentation = preload("res://scripts/book_presentation_v172.gd")
var item_id := ""
var display_name := ""
var visual_node: Node3D
var presentation_id := ""
var remove_before_acquire := false

func interact() -> void:
    if item_id.is_empty() or DemoState.has(item_id):
        return
    if remove_before_acquire and is_instance_valid(visual_node):
        visual_node.visible = false
    DemoState.acquire(item_id)
    if not remove_before_acquire and is_instance_valid(visual_node):
        visual_node.visible = false
    if not presentation_id.is_empty():
        BookPresentation.open(get_tree().current_scene, presentation_id)
    print("Picked up: ", display_name if not display_name.is_empty() else item_id)
    queue_free()

func interaction_cursor_id() -> String:
    return "TAKE"
