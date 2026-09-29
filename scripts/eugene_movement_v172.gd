extends Node
class_name EugeneMovementV172

const SOURCE_SPEED := 12.0
const SOURCE_CANDIDATE_DISTANCE := 80.0
const SOURCE_RUN_MIN := 2
const SOURCE_RUN_MAX := 7

var source_direction := Vector3.ZERO
var remaining_run_steps := 0
var prng_status := "HOLD_EXACT_INITIALIZATION"
var model_front_calibration := "HOLD_SOURCE_PROOF"

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

func can_autogenerate_heading() -> bool:
    # Exact legacy PRNG initialization is not source-proven yet.  Never replace
    # it with Godot RNG or a guessed seed because that changes NPC trajectories.
    return false
