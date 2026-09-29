extends Node
class_name LegacyRandV174

const MULTIPLIER := 0x41C64E6D
const INCREMENT := 0x3039
const DEFAULT_NEXT := 1

var _next: int = DEFAULT_NEXT
var _call_index := 0

func reset_default() -> void:
    _next = DEFAULT_NEXT
    _call_index = 0

func srand_compat(seed: int) -> void:
    _next = seed & 0xFFFFFFFF
    _call_index = 0

func rand_compat() -> int:
    _next = int((_next * MULTIPLIER + INCREMENT) & 0xFFFFFFFF)
    _call_index += 1
    return int((_next >> 16) & 0x7FFF)

func rand_mod(modulus: int) -> int:
    if modulus <= 0:
        return 0
    return rand_compat() % modulus

func call_index() -> int:
    return _call_index

func state_u32() -> int:
    return _next

func initialization_status() -> String:
    # R.EXE/Open Watcom default static state is source-backed.  What remains
    # unresolved is the global rand() call index when Eugene first requests a
    # heading; do not reset this stream per NPC or per room.
    return "DEFAULT_NEXT_1_SOURCE_BACKED_GLOBAL_CALL_INDEX_HOLD"
