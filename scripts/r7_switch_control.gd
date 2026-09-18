extends Area3D

var control_id := ""
var visual_node: Node3D

func interact() -> void:
    var result := DemoState.switchboard_step(control_id)
    match result:
        "solved":
            print("The pipe locks into its new position. Water can be heard draining in the Baptistery. [R8BathDrain]")
        "correct":
            print("The switchboard setting moves into the correct position.")
        "reset":
            print("That is not the plaque sequence. The switchboard resets.")
        "already_solved":
            print("The switchboard is already configured.")
