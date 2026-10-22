extends Node
class_name EugeneMovementV172

const SOURCE_SPEED := 12.0
const SOURCE_CANDIDATE_DISTANCE := 80.0
const SOURCE_RUN_MIN := 2
const SOURCE_RUN_MAX := 7
const SOURCE_RECOVERY_UPDATES := 50

var source_direction := Vector3.ZERO
var remaining_run_steps := 0
var prng_status := "GLOBAL_WATCOM_STREAM_V192_NO_LOCAL_RESET"
var model_front_calibration := "SOURCE_XAF_V188_LOCAL_PLUS_X_ROOT_TRANSFORM"

func configure(direction: Vector3) -> void:
    source_direction = direction.normalized()

func source_step_delta() -> Vector3:
    return source_direction * SOURCE_SPEED

func candidate_endpoint(origin: Vector3, candidate_direction: Vector3) -> Vector3:
    return origin + candidate_direction.normalized() * SOURCE_CANDIDATE_DISTANCE

func accept_source_heading(candidate_direction: Vector3, run_steps: int) -> bool:
    if candidate_direction.length_squared() <= 0.0:
        return false
    if run_steps < SOURCE_RUN_MIN or run_steps > SOURCE_RUN_MAX:
        return false
    source_direction = candidate_direction.normalized()
    remaining_run_steps = run_steps
    return true

func consume_source_step() -> Vector3:
    if remaining_run_steps <= 0:
        return Vector3.ZERO
    remaining_run_steps -= 1
    return source_step_delta()

func heading_degrees_from_legacy_rand(legacy_rand: Node) -> int:
    if legacy_rand == null or not legacy_rand.has_method("rand_mod"):
        return -1
    return int(legacy_rand.call("rand_mod", 360))

func heading_direction_from_degrees(degrees: int) -> Vector3:
    var radians := deg_to_rad(float(degrees))
    return Vector3(cos(radians), 0.0, sin(radians)).normalized()

func executable_movement_proof_status() -> String:
    return "R_EXE_V185_RANDOMMOVEMENT_0x86780_RAND_0x97F85_HEADING_MOD_360_VERIFIED"

func can_autogenerate_heading() -> bool:
    # LCG/default next=1 are source-backed, but Eugene's exact position in the
    # shared global rand() call stream is not yet proven. Never reset per NPC.
    return false

func startup_random_movement_status() -> String:
    return "R_EXE_V192_COUNTDOWN_0_DEFAULT_RECOVERY_50_SHARED_GLOBAL_RAND"

func source_recovery_update_count() -> int:
    return SOURCE_RECOVERY_UPDATES

func random_heading_from_shared_stream(legacy_rand: Node) -> Vector3:
    # Invoke only from a source-backed RandomMovement path; never reset here.
    var degrees := heading_degrees_from_legacy_rand(legacy_rand)
    return Vector3.ZERO if degrees < 0 else heading_direction_from_degrees(degrees)
