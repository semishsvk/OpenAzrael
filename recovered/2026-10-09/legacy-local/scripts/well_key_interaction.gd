extends Area3D

signal demo_action_step(step: String)

var key_visual: Node3D

func _step(value: String) -> void:
    demo_action_step.emit(value)

func interact() -> void:
    if DemoState.has("well_key"):
        return
    if not DemoState.has("rusty_tongs"):
        print(LocalizationManager.tr_key("interaction.r7.key_out_of_reach"))
        return

    # Recovered verbatim from the official demo's compiled WORLD action group:
    # 0x08 R7Key -> 0x28 979TONGS -> 0x07 R7Key ->
    # 0x08 RustyTongR6 -> 0x09 TongR6.
    #
    # The original dispatcher executes these records in one pending-group pass.
    # There is no transform/rotation animation opcode in this event, so do not
    # invent a Tween. The observable timed feedback is the original 979TONGS
    # sample while the authored room/inventory state swap is applied.
    if is_instance_valid(key_visual):
        key_visual.visible = false
    _step("remove_room:R7Key")

    LegacyEvents.run("R7_WELL_TONGS_USE")
    _step("play_sound:979TONGS.WAV")

    if is_instance_valid(key_visual):
        key_visual.visible = true
    _step("add_room:R7Key")

    # RustyTongR6 is an authored transient room-state object in the demo
    # (WORLD section0 1245) with no XAF mesh name. Preserve its state transition
    # semantically rather than fabricating a visible model.
    _step("remove_room:RustyTongR6")

    DemoState.remove("rusty_tongs")
    _step("remove_inventory:TONG6")

    if DemoState.complete_well_key_take():
        # Default TAKE completes after the compiled action group: the key ends
        # in inventory and therefore is no longer visible in the room.
        if is_instance_valid(key_visual):
            key_visual.visible = false
        _step("default_take:R7Key")
        print(LocalizationManager.tr_key("interaction.r7.key_retrieved"))
        queue_free()

func interaction_cursor_id() -> String:
    if DemoState.has("well_key"):
        return "CANT"
    return "USE" if DemoState.has("rusty_tongs") else "CANT"
