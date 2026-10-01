extends Area3D
## Pickup adapter for source objects whose original WORLD action group ends in
## opcode 0x21 (generic book view). State acquisition is applied first; the
## source-backed presentation is then opened before this interaction node exits.
const BookPresentation = preload("res://scripts/book_presentation_v172.gd")
var item_id := ""
var display_name := ""
var visual_node: Node3D
var presentation_id := ""

func interact() -> void:
    if item_id.is_empty() or DemoState.has(item_id):
        return
    DemoState.acquire(item_id)
    if is_instance_valid(visual_node):
        visual_node.visible = false
    if not presentation_id.is_empty():
        BookPresentation.open(get_tree().current_scene, presentation_id)
    print("Picked up: ", display_name if not display_name.is_empty() else item_id)
    queue_free()

func interaction_cursor_id() -> String:
    return "TAKE"
