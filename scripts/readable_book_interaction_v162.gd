extends Area3D
## Source-backed R1 parchment interaction.
## Verified WORLD lifecycle: 0x07 remove/deactivate -> 0x08 add carried -> 0x21 book view.
const BookPresentation = preload("res://scripts/book_presentation_v172.gd")
const PRESENTATION_ID := "R1/r1p1"
const ITEM_ID := "parchment_r1"
var visual_node: Node3D

func interact() -> void:
    if DemoState.has(ITEM_ID):
        return
    if is_instance_valid(visual_node):
        visual_node.visible = false
    DemoState.acquire(ITEM_ID)
    BookPresentation.open(get_tree().current_scene, PRESENTATION_ID)
    queue_free()

func interaction_cursor_id() -> String:
    return "LOOK"
