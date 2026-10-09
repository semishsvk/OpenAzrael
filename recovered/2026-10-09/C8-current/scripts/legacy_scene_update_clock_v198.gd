extends Node
class_name LegacySceneUpdateClockV198

signal legacy_scene_update_pass(pass_index: int)

var _drivers: Array[Node] = []
var _pass_index := 0

func register_source_frame_driver(driver: Node) -> bool:
    if driver == null or not is_instance_valid(driver):
        return false
    if not driver.has_method("source_update"):
        return false
    if _drivers.has(driver):
        return true
    _drivers.append(driver)
    return true

func unregister_source_frame_driver(driver: Node) -> void:
    _drivers.erase(driver)

func dispatch_eligible_legacy_scene_update_pass() -> int:
    # v197 source semantics: one source-frame update is eligible when the
    # original scene callback dispatcher runs on an eligible gameplay pass.
    # This object deliberately owns no wall-clock, process or physics cadence.
    _pass_index += 1
    legacy_scene_update_pass.emit(_pass_index)
    var advanced := 0
    var keep: Array[Node] = []
    for driver in _drivers:
        if driver == null or not is_instance_valid(driver):
            continue
        keep.append(driver)
        if bool(driver.call("source_update")):
            advanced += 1
    _drivers = keep
    return advanced

func pass_index() -> int:
    return _pass_index

func registered_driver_count() -> int:
    return _drivers.size()
