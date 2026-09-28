extends Area3D

var bible_visual: Node3D
var installed_lens_visual: Node3D
var look_lens_visual: Node3D
var player: Node3D
var activation_center := Vector3.ZERO
var activation_half_extents := Vector3(12.0, 80.0, 12.0)
var door_visual: Node3D
var shield_visual: Node3D
var shield_interaction: Area3D
var sequence_running := false

# v18: do NOT use the nearby 0x0726/1830 token tag as milliseconds; it is compiler/source metadata.
const RAISE_PROXY_SECONDS := 3.3980952381
const SECRET_DOOR_SECONDS := 3.5907482993

func _play_one_shot(stream: AudioStream) -> void:
    var p := AudioStreamPlayer.new()
    p.stream = stream
    get_tree().current_scene.add_child(p)
    p.finished.connect(p.queue_free)
    p.play()

func _on_activation_zone() -> bool:
    if not is_instance_valid(player):
        return false
    var p := player.global_position
    return abs(p.x - activation_center.x) <= activation_half_extents.x \
        and abs(p.z - activation_center.z) <= activation_half_extents.z \
        and abs(p.y - activation_center.y) <= activation_half_extents.y

func _run_optical_sequence() -> void:
    if sequence_running or DemoState.puzzle_node("DoorR8"):
        return
    sequence_running = true
    LegacyEvents.run("R8_OPTICAL_START")
    print("Optical mechanism starts. [R8LensLook -> R8RaiseTimer]")

    # Retail OBJECTS.DAT maps R8LensPlace -> lenstop and R8LensLook -> lenstop01.
    # They are effectively the same mesh authored at two poses. Animate between the
    # exact authored poses; only the interpolation/timing remains reconstruction.
    if is_instance_valid(installed_lens_visual) and is_instance_valid(look_lens_visual):
        look_lens_visual.visible = false
        var target := look_lens_visual.global_transform
        var tw_lens := create_tween()
        tw_lens.set_trans(Tween.TRANS_SINE)
        tw_lens.set_ease(Tween.EASE_IN_OUT)
        tw_lens.tween_property(installed_lens_visual, "global_transform", target, RAISE_PROXY_SECONDS)

    await get_tree().create_timer(RAISE_PROXY_SECONDS).timeout
    LegacyEvents.run("R8_SECRET_DOOR_OPEN")

    # Retail OBJECTS.DAT maps DoorR8 directly to XAF object "door". The door's
    # local X bounds start ~0 at one edge, giving us an authored hinge pivot.
    # v18 geometry sweep prefers +90: -90 swings into the Shield-chamber footprint.
    if is_instance_valid(door_visual):
        var tw := create_tween()
        tw.set_trans(Tween.TRANS_SINE)
        tw.set_ease(Tween.EASE_IN_OUT)
        tw.tween_property(door_visual, "rotation:y", door_visual.rotation.y + deg_to_rad(90.0), SECRET_DOOR_SECONDS)
    if is_instance_valid(shield_visual):
        shield_visual.visible = true
    if is_instance_valid(shield_interaction):
        shield_interaction.collision_layer = 2
    await get_tree().create_timer(SECRET_DOOR_SECONDS).timeout
    sequence_running = false
    print("Secret DoorR8 open. Shield exposed.")

func interact() -> void:
    if not DemoState.puzzle_node("R8LensPlace"):
        if not DemoState.has("r8_lens"):
            print("The stone Bible has a place for a lens.")
            return
        LegacyEvents.run("R8_LENS_PLACE")
        if is_instance_valid(installed_lens_visual):
            installed_lens_visual.visible = true
        if is_instance_valid(look_lens_visual):
            look_lens_visual.visible = false
        print("Placed the lens on the stone Bible. [R8LensPlace -> lenstop]")
        return

    if DemoState.puzzle_node("DoorR8"):
        print("The optical mechanism has already opened the secret door.")
        return
    if sequence_running:
        return
    if not _on_activation_zone():
        print("The lens is in place, but the mechanism does not engage. Stand inside the original zxplate trigger.")
        return

    _run_optical_sequence()

func interaction_cursor_id() -> String:
    if not DemoState.puzzle_node("R8LensPlace"):
        return "USE" if DemoState.has("r8_lens") else "CANT"
    if DemoState.puzzle_node("DoorR8") or sequence_running:
        return "CANT"
    return "USE" if _on_activation_zone() else "CANT"
