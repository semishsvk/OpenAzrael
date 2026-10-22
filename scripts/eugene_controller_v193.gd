extends CharacterBody3D
class_name EugeneControllerV193

const SOURCE_STEP := 12.0
const SOURCE_CANDIDATE_DISTANCE := 80.0
const SOURCE_RECOVERY_UPDATES := 50
const SOURCE_MAX_HEADING_ATTEMPTS := 20

var source_direction := Vector3.ZERO
var recovery_updates := 0
var shared_rand: Node = null
var movement: Node = null
var source_animation_player: AnimationPlayer = null
var _source_animation_family := ""
var source_movement_armed := false

func configure(direction: Vector3, rand_service: Node, movement_helper: Node) -> void:
    # NPC*.DAT direction is source-authored facing/state.  It is not, by
    # itself, executable proof that autonomous movement begins at spawn.
    source_direction = direction.normalized()
    shared_rand = rand_service
    movement = movement_helper
    source_movement_armed = false

func arm_source_movement() -> void:
    # Call only from an executable/source-backed movement action.  Spawn does
    # not arm autonomous movement (R.EXE v191/v192 evidence).
    source_movement_armed = true

func disarm_source_movement() -> void:
    source_movement_armed = false
    _play_source_family("REST")

func bind_source_animation_player(player: AnimationPlayer) -> void:
    source_animation_player = player
    _play_source_family("REST")

func _play_source_family(family: String) -> void:
    if source_animation_player == null or not is_instance_valid(source_animation_player):
        return
    if _source_animation_family == family and source_animation_player.is_playing():
        return
    if not source_animation_player.has_animation(StringName(family)):
        return
    source_animation_player.play(StringName(family))
    _source_animation_family = family

func _horizontal_motion(direction: Vector3, distance: float) -> Vector3:
    var d := Vector3(direction.x, 0.0, direction.z).normalized()
    return d * distance

func _blocked(direction: Vector3, distance: float) -> bool:
    var motion := _horizontal_motion(direction, distance)
    return motion.length_squared() > 0.0 and test_move(global_transform, motion)

func _arm_recovery() -> void:
    if recovery_updates == 0:
        recovery_updates = SOURCE_RECOVERY_UPDATES
        CandidateDiagnostics.record_event("eugene_recovery_armed", {
            "character": String(name),
            "updates": SOURCE_RECOVERY_UPDATES,
            "status": "SOURCE_V192_COLLISION_RECOVERY"
        })

func _try_source_random_heading() -> void:
    if shared_rand == null:
        return
    for _attempt in range(SOURCE_MAX_HEADING_ATTEMPTS):
        var degrees := int(shared_rand.call("rand_mod", 360))
        var radians := deg_to_rad(float(degrees))
        var candidate := Vector3(cos(radians), 0.0, sin(radians)).normalized()
        if not _blocked(candidate, SOURCE_CANDIDATE_DISTANCE):
            source_direction = candidate
            if movement != null:
                movement.call("configure", candidate)
            return

func _source_recovery_update() -> void:
    if recovery_updates <= 0:
        return
    _try_source_random_heading()
    recovery_updates -= 1
    if recovery_updates == 0:
        CandidateDiagnostics.record_event("eugene_recovery_complete", {
            "character": String(name),
            "status": "SOURCE_V192_50_UPDATES_COMPLETE"
        })

func _physics_process(_delta: float) -> void:
    if recovery_updates > 0:
        _play_source_family("REST")
        _source_recovery_update()
        return
    if not source_movement_armed:
        _play_source_family("REST")
        return
    if source_direction.length_squared() <= 0.0:
        return
    var motion := _horizontal_motion(source_direction, SOURCE_STEP)
    if test_move(global_transform, motion):
        _play_source_family("REST")
        _arm_recovery()
        return
    # Use CharacterBody3D collision-aware movement even after the preflight
    # test. Direct global_position writes would bypass production physics.
    _play_source_family("RUN")
    move_and_collide(motion)

func recovery_updates_remaining() -> int:
    return recovery_updates

func movement_is_armed() -> bool:
    return source_movement_armed

func shared_rng_call_index() -> int:
    if shared_rand == null or not shared_rand.has_method("call_index"):
        return -1
    return int(shared_rand.call("call_index"))
