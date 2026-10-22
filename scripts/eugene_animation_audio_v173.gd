extends Node
class_name EugeneAnimationAudioV173

signal source_effect_requested(value: int, source: String)

const CONTRACT_PATH := "res://data/tests/kg001_eugene_animation_audio_contract_v173.json"
const AUDIO_PATH := "res://assets/audio/EUGROAR.WAV"

var contract: Dictionary = {}
var current_family := ""
var previous_frame := -1
var roar_fired_for_cycle := false
var audio_player: AudioStreamPlayer3D
var source_frame_driver: Node = null

func _ready() -> void:
    var parsed = JSON.parse_string(FileAccess.get_file_as_string(CONTRACT_PATH))
    contract = parsed if parsed is Dictionary else {}
    audio_player = AudioStreamPlayer3D.new()
    audio_player.name = "EugeneSourceAudio"
    add_child(audio_player)

func bind_source_frame_driver(driver: Node) -> bool:
    if driver == null or not is_instance_valid(driver):
        return false
    if not driver.has_signal("source_frame_observed"):
        return false
    if source_frame_driver != null and is_instance_valid(source_frame_driver):
        var old_callable := Callable(self, "_on_source_frame_observed")
        if source_frame_driver.is_connected("source_frame_observed", old_callable):
            source_frame_driver.disconnect("source_frame_observed", old_callable)
    source_frame_driver = driver
    var callback := Callable(self, "_on_source_frame_observed")
    if not source_frame_driver.is_connected("source_frame_observed", callback):
        source_frame_driver.connect("source_frame_observed", callback)
    return true

func _on_source_frame_observed(family: String, frame: int) -> void:
    if family != current_family:
        if not begin_source_family(family):
            current_family = ""
            return
    observe_source_frame(frame)

func begin_source_family(family: String) -> bool:
    if not contract.get("families", {}).has(family):
        return false
    current_family = family
    previous_frame = int(contract["families"][family][0]) - 1
    roar_fired_for_cycle = false
    return true

func observe_source_frame(frame: int) -> void:
    if current_family.is_empty():
        return
    var bounds: Array = contract.get("families", {}).get(current_family, [])
    if bounds.size() != 2 or frame < int(bounds[0]) or frame > int(bounds[1]):
        return
    var trigger: Dictionary = contract.get("trigger", {})
    var trigger_frame := int(trigger.get("frame", -1))
    if (
        not roar_fired_for_cycle
        and previous_frame < trigger_frame
        and frame >= trigger_frame
        and String(trigger.get("sound", "")) == "EUGROAR.WAV"
    ):
        _play_source_roar()
        source_effect_requested.emit(int(trigger.get("parameter", 0)), "EUGROAR_FRAME_60")
        CandidateDiagnostics.record_event("eugene_trigger_effect", {"status":"SOURCE_PLAYER_HEALTH_DAMAGE_REQUESTED", "frame":trigger_frame, "value":int(trigger.get("parameter", 0))})
        roar_fired_for_cycle = true
    previous_frame = frame

func _play_source_roar() -> void:
    if not ResourceLoader.exists(AUDIO_PATH):
        CandidateDiagnostics.record_event("eugene_audio", {"status":"HOLD_SOURCE_ASSET", "sound":"EUGROAR.WAV", "frame":60})
        return
    var stream := load(AUDIO_PATH) as AudioStream
    if stream == null:
        return
    audio_player.stream = stream
    audio_player.play()
    CandidateDiagnostics.record_event("eugene_audio", {"status":"PLAYING_SOURCE_AUDIO", "sound":"EUGROAR.WAV", "frame":60})

func can_synthesize_missing_animation() -> bool:
    return false
