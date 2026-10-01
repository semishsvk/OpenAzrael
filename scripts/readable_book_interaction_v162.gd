extends Area3D
## Source-backed world LOOK for R1/r1p1.
## Original opcode 0x21 routes this object through the generic book subsystem.
const BookPresentation = preload("res://scripts/book_presentation_v172.gd")
const PRESENTATION_ID := "R1/r1p1"

func interact() -> void:
    BookPresentation.open(get_tree().current_scene, PRESENTATION_ID)

func interaction_cursor_id() -> String:
    return "LOOK"
