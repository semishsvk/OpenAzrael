extends SceneTree

var failed: Array[String] = []

func _check(ok: bool, label: String) -> void:
    if not ok:
        failed.append(label)

func _initialize() -> void:
    call_deferred("_run")

func _run() -> void:
    var world := Node3D.new()
    world.name = "EugeneV194HeadlessWorld"
    root.add_child(world)

    var floor_body := StaticBody3D.new()
    var wall_shape := CollisionShape3D.new()
    var wall_box := BoxShape3D.new()
    wall_box.size = Vector3(2.0, 40.0, 40.0)
    wall_shape.shape = wall_box
    floor_body.add_child(wall_shape)
    floor_body.position = Vector3(10.0, 0.0, 0.0)
    world.add_child(floor_body)

    var rng := Node.new()
    rng.name = "LegacyGlobalRand"
    rng.set_script(load("res://scripts/legacy_rand_v174.gd"))
    world.add_child(rng)

    var movement := Node.new()
    movement.set_script(load("res://scripts/eugene_movement_v172.gd"))
    world.add_child(movement)

    var eugene := CharacterBody3D.new()
    eugene.name = "EugeneV194"
    eugene.collision_layer = 8
    eugene.collision_mask = 1
    eugene.set_script(load("res://scripts/eugene_controller_v193.gd"))
    var shape := CollisionShape3D.new()
    var capsule := CapsuleShape3D.new()
    capsule.radius = 1.0
    capsule.height = 4.0
    shape.shape = capsule
    eugene.add_child(shape)
    world.add_child(eugene)
    eugene.call("configure", Vector3.RIGHT, rng, movement)

    var spawn_position := eugene.global_position
    await physics_frame
    await physics_frame
    _check(int(eugene.call("shared_rng_call_index")) == 0, "spawn_consumed_rng")
    _check(not bool(eugene.call("movement_is_armed")), "spawn_armed_movement")
    _check(eugene.global_position.is_equal_approx(spawn_position), "spawn_direction_caused_movement")

    # The harness explicitly arms the movement input under test.  This is not
    # evidence that spawn itself arms movement; v191/v192 prove the opposite.
    eugene.call("arm_source_movement")
    _check(bool(eugene.call("movement_is_armed")), "explicit_movement_arm_failed")
    await physics_frame
    _check(int(eugene.call("recovery_updates_remaining")) == 50, "collision_did_not_arm_50")
    var before := int(eugene.call("shared_rng_call_index"))
    for _i in range(50):
        await physics_frame
    _check(int(eugene.call("recovery_updates_remaining")) == 0, "recovery_not_exactly_50_updates")
    var after := int(eugene.call("shared_rng_call_index"))
    _check(after > before, "recovery_did_not_consume_shared_rng")
    _check(rng.call("call_index") == after, "controller_not_using_shared_rng_instance")

    var result := {
        "schema": "openazrael.kg001.eugene_headless_runtime_v194",
        "status": "PASS" if failed.is_empty() else "FAIL",
        "failed": failed,
        "spawn_stationary": eugene.global_position.is_equal_approx(spawn_position),
        "rng_before_recovery": before,
        "rng_after_recovery": after,
        "recovery_updates": 50,
        "scope": "GODOT_HEADLESS_CONTROLLER_PHYSICS_NOT_R1_E2E"
    }
    print(JSON.stringify(result))
    quit(0 if failed.is_empty() else 1)
