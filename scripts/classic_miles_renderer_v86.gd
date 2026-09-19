class_name ClassicMilesRendererV86
extends RefCounted

# Activation-ready Classic renderer adapter.
# Converts reconstructed Miles integer controls to Godot controls without
# changing the forensic reference math. Kept behind an explicit opt-in gate
# until a real original-runtime v80/v84 parity capture passes.

const MILES_PAN_MIN := 1
const MILES_PAN_CENTER := 64
const MILES_PAN_MAX := 127
const MILES_VOLUME_MAX := 127

static func miles_pan_to_godot_pan(pan: int) -> float:
    # Miles center=64; reconstructed Classic path currently yields 1..127.
    return clamp((float(pan) - float(MILES_PAN_CENTER)) / 63.0, -1.0, 1.0)

static func miles_volume_to_db(volume: int) -> float:
    var v: int = clamp(volume, 0, MILES_VOLUME_MAX)
    if v <= 0:
        return -80.0
    return linear_to_db(float(v) / float(MILES_VOLUME_MAX))

static func configure_bus(bus_index: int, pan: int) -> void:
    if bus_index < 0:
        return
    if AudioServer.get_bus_effect_count(bus_index) == 0 or not (AudioServer.get_bus_effect(bus_index, 0) is AudioEffectPanner):
        AudioServer.add_bus_effect(bus_index, AudioEffectPanner.new(), 0)
    var fx := AudioServer.get_bus_effect(bus_index, 0) as AudioEffectPanner
    fx.pan = miles_pan_to_godot_pan(pan)
