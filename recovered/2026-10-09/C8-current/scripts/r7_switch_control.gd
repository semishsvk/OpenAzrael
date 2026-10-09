extends Area3D

var control_id := ""
var visual_node: Node3D

func interact() -> void:
    var step_before := int(DemoState.value("R7SwitchStep", 0))
    var result := DemoState.switchboard_step(control_id)
    if result in ["correct", "solved"]:
        if step_before == 0 and control_id == "well_lev02":
            LegacyEvents.run("R7_SWITCH_LEVER_PULL_SOUND")
        elif step_before == 1 and control_id == "well_weel3":
            LegacyEvents.run("R7_SWITCH_WHEEL_TURN_SOUND")
        elif step_before == 2 and control_id == "well_lev02":
            LegacyEvents.run("R7_SWITCH_LEVER_PUSH_SOUND")
            LegacyEvents.run("R7_WATER_CONNECTED_SOUND")
    match result:
        "solved":
            print("The pipe locks into its new position. Water can be heard draining in the Baptistery. [R8BathDrain]")
        "correct":
            print("The switchboard setting moves into the correct position.")
        "reset":
            print("That is not the plaque sequence. The switchboard resets.")
        "already_solved":
            print("The switchboard is already configured.")

func interaction_cursor_id() -> String:
    if DemoState.flag("R8BathDrain"):
        return "CANT"
    if control_id == "well_lev02":
        return "PUSH" if int(DemoState.value("R7SwitchStep", 0)) == 2 else "PULL"
    if control_id == "well_weel3":
        return "ROT"
    return "USE"
