extends Area3D

var control_id := ""
var visual_node: Node3D

func interact() -> void:
    if control_id == "well_lev02":
        LegacyEvents.run("R7_SWITCH_LEVER_PULL")
    elif control_id == "well_weel3":
        LegacyEvents.run("R7_SWITCH_WHEEL_TURN")
    var result := DemoState.switchboard_step(control_id)
    match result:
        "solved":
            print(LocalizationManager.tr_key("puzzle.r7.pipe_drained"))
        "correct":
            print(LocalizationManager.tr_key("puzzle.r7.switch_correct"))
        "reset":
            print(LocalizationManager.tr_key("puzzle.r7.switch_reset"))
        "already_solved":
            print(LocalizationManager.tr_key("puzzle.r7.switch_done"))

func interaction_cursor_id() -> String:
    if DemoState.flag("R8BathDrain"):
        return "CANT"
    if control_id == "well_lev02":
        return "PULL"
    if control_id == "well_weel3":
        return "ROT"
    return "USE"
