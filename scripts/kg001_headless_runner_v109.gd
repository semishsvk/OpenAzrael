extends SceneTree

const INITIAL_HASH := "90fdebf6dff29bf2b4b78980615205c2e6c067b65a28c2aff0b7f10b513f6abf"
const COMPLETE_HASH := "e266137c74746996608ffcdd165b6a1072e2c9f55833473546061ccac0e05902"
const EXPECTED_AUDIO := ["979TONGS.WAV", "S152V2.WAV", "S137.WAV", "S121.WAV", "799SECDR.WAV"]

var failures: Array[String] = []

func _initialize() -> void:
    call_deferred("_run")

func _check(name: String, condition: bool) -> void:
    if not condition:
        failures.append(name)

func _run() -> void:
    var state = root.get_node_or_null("DemoState")
    var events = root.get_node_or_null("LegacyEvents")
    if state == null or events == null:
        print(JSON.stringify({"version":109,"status":"FAIL","error":"required autoload missing"}))
        quit(1)
        return

    events.set_capture_only(true)
    events.clear_capture()
    state.reset_all()

    _check("initial_hash", state.canonical_state_hash() == INITIAL_HASH)

    state.acquire("rusty_tongs")
    state.set_flag("R1Door1Open")
    events.run("R7_WELL_TONGS_USE")
    _check("retrieve_well_key", state.retrieve_well_key())
    _check("switch_1", state.switchboard_step("well_lev02") == "correct")
    _check("switch_2", state.switchboard_step("well_weel3") == "correct")
    _check("switch_3", state.switchboard_step("well_lev02") == "solved")
    _check("unlock_demo_door", state.unlock_demo_door())

    state.acquire("r8_lens")
    state.set_flag("R8Lens")
    events.run("R8_LENS_PLACE")
    events.run("R8_OPTICAL_START")
    events.run("R8_SECRET_DOOR_OPEN")
    events.run("R8_TAKE_SHIELD")

    _check("demo_complete", state.flag("demo_complete"))
    _check("complete_hash", state.canonical_state_hash() == COMPLETE_HASH)
    _check("logical_audio_stream", events.captured_audio() == EXPECTED_AUDIO)

    var saved_payload: Array = state.canonical_state_payload().duplicate(true)
    var saved_hash := state.canonical_state_hash()
    state.reset_all()
    _check("reset_hash", state.canonical_state_hash() == INITIAL_HASH)
    _check("restore_payload", state.restore_canonical_state_payload(saved_payload))
    _check("restore_hash", state.canonical_state_hash() == saved_hash)
    _check("restore_complete", state.flag("demo_complete"))

    var result := {
        "schema": "openazrael.kg001.headless",
        "version": 109,
        "status": "PASS" if failures.is_empty() else "FAIL",
        "checks": 13,
        "failed": failures,
        "persistent_hash": state.canonical_state_hash(),
        "logical_audio_events": events.captured_audio(),
        "scope": "autoload/Event-IR/state round-trip; main scene and commercial-derived assets are not loaded"
    }
    print("OPENAZRAEL_KG001_V109 " + JSON.stringify(result))
    quit(0 if failures.is_empty() else 1)
