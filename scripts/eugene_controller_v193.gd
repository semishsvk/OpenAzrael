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

func configure(direction: Vector3, rand_service: Node, movement_helper: Node) -> void:
    source_direction = direction.normalized()
    shared_rand = rand_service
    movement = movement_helper

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
    # R.EXE v185: RandomMovement probes headings from the process-global
    # Watcom rand stream and limits heading-search work to 20 attempts.
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
    if source_direction.length_squared() <= 0.0:
        return
    if recovery_updates > 0:
        _source_recovery_update()
        return
    var motion := _horizontal_motion(source_direction, SOURCE_STEP)
    if test_move(global_transform, motion):
        _arm_recovery()
        return
    global_position += motion

func recovery_updates_remaining() -> int:
    return recovery_updates

func shared_rng_call_index() -> int:
    if shared_rand == null or not shared_rand.has_method("call_index"):
        return -1
    return int(shared_rand.call("call_index"))
