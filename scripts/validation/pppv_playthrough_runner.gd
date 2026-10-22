extends SceneTree

const EvidenceBusScript = preload("res://scripts/validation/pppv_evidence_bus.gd")
const PlayerDriverScript = preload("res://scripts/validation/pppv_player_driver.gd")
const NavigatorScript = preload("res://scripts/validation/pppv_navigator.gd")
const ObserverScript = preload("res://scripts/validation/openazrael_pppv_observer.gd")
const SceneObserverScript = preload("res://scripts/validation/pppv_scene_observer.gd")
const ActionExecutorScript = preload("res://scripts/validation/pppv_action_executor.gd")
const RuntimeGuardScript = preload("res://scripts/validation/pppv_runtime_guard.gd")

var failures: Array[String] = []
var proof_enabled := false
var proof_label: Label = null

func _arg_enabled(flag: String) -> bool:
    for arg in OS.get_cmdline_args() + OS.get_cmdline_user_args():
        if arg == flag or arg == flag + "=1" or arg == flag + "=true":
            return true
    return false

func _proof_overlay_create() -> void:
    if not proof_enabled:
        return
    var layer := CanvasLayer.new()
    layer.name = "PPPVProofCaptureOverlay"
    layer.layer = 1000
    root.add_child(layer)

    var background := ColorRect.new()
    background.name = "Background"
    background.position = Vector2(12, 620)
    background.size = Vector2(1256, 88)
    background.color = Color(0.0, 0.0, 0.0, 0.72)
    layer.add_child(background)

    proof_label = Label.new()
    proof_label.name = "Status"
    proof_label.position = Vector2(24, 628)
    proof_label.size = Vector2(1232, 72)
    proof_label.add_theme_font_size_override("font_size", 18)
    proof_label.add_theme_color_override("font_color", Color(1.0, 1.0, 1.0, 1.0))
    proof_label.add_theme_color_override("font_outline_color", Color(0.0, 0.0, 0.0, 1.0))
    proof_label.add_theme_constant_override("outline_size", 4)
    layer.add_child(proof_label)

func _proof_overlay_update(step: Dictionary, manager: Node, status: String) -> void:
    if not proof_enabled or proof_label == null:
        return
    var sha := OS.get_environment("OPENAZRAEL_PROOF_GIT_SHA")
    if sha.is_empty():
        sha = "UNKNOWN"
    var sha_short := sha.substr(0, min(12, sha.length()))
    var freeze_sha := OS.get_environment("OPENAZRAEL_PROOF_FREEZE_SHA")
    var freeze_short := (
        freeze_sha.substr(0, min(12, freeze_sha.length()))
        if not freeze_sha.is_empty()
        else "UNKNOWN"
    )
    var room := (
        String(manager.get("current_room_id"))
        if manager != null
        else "UNKNOWN"
    )
    var step_id := String(step.get("step_id", "BOOT"))
    proof_label.text = (
        "OpenAzrael KG-001 Candidate 4 | REAL PPPV PROOF CAPTURE\n"
        + "SHA " + sha_short
        + " | FREEZE " + freeze_short
        + " | ROOM " + room
        + " | STEP " + step_id
        + " | " + status
    )

func _initialize() -> void:
    call_deferred("_run")

func _arg_value(prefix: String, default_value: String = "") -> String:
    for arg in OS.get_cmdline_args() + OS.get_cmdline_user_args():
        if arg.begins_with(prefix):
            return arg.substr(prefix.length())
    return default_value

func _load_json(path: String) -> Dictionary:
    if path.is_empty() or not FileAccess.file_exists(path):
        return {}
    var parsed = JSON.parse_string(FileAccess.get_file_as_string(path))
    return parsed if parsed is Dictionary else {}

func _write_json(path: String, payload: Dictionary) -> bool:
    var file := FileAccess.open(path, FileAccess.WRITE)
    if file == null:
        return false
    file.store_string(JSON.stringify(payload, "  ") + "\n")
    file.close()
    return true

func _settle(frames: int = 2) -> void:
    for _i in range(frames):
        await process_frame

func _scenario_map(bundle: Dictionary) -> Dictionary:
    var out: Dictionary = {}
    for raw in bundle.get("scenarios", []):
        if not raw is Dictionary:
            continue
        var scenario_id := String(raw.get("scenario_id", ""))
        if not scenario_id.is_empty():
            out[scenario_id] = raw
    return out

func _known_state_keys(scenario: Dictionary) -> Dictionary:
    var inventory_keys: Array[String] = []
    var flag_keys: Array[String] = []
    var puzzle_keys: Array[String] = []
    var out := {
        "inventory": inventory_keys,
        "flags": flag_keys,
        "puzzle": puzzle_keys
    }
    for row in scenario.get("state_expectations", []):
        if not row is Dictionary:
            continue
        var path := String(row.get("path", ""))
        var pieces := path.split(".", false, 1)
        if pieces.size() != 2:
            continue
        var group := String(pieces[0])
        var key := String(pieces[1])
        if group == "inventory" and not out["inventory"].has(key):
            out["inventory"].append(key)
        elif group == "flags" and not out["flags"].has(key):
            out["flags"].append(key)
        elif group == "puzzle" and not out["puzzle"].has(key):
            out["puzzle"].append(key)
    return out

func _precondition_value(state: Node, group: String, key: String):
    match group:
        "inventory":
            return bool(state.call("has", key))
        "flags":
            return bool(state.call("flag", key))
        "puzzle":
            return bool(state.call("puzzle_node", key))
        "values":
            return state.call("value", key, null)
    return null

func _check_setup_preconditions(
    scenario: Dictionary,
    state: Node
) -> Array[String]:
    var errors: Array[String] = []
    var setup = scenario.get("setup", {})
    if not setup is Dictionary:
        return errors

    for group in ["inventory", "flags", "puzzle", "values"]:
        var expected = setup.get(group, {})
        if not expected is Dictionary:
            continue
        for raw_key in expected.keys():
            var key := String(raw_key)
            var actual = _precondition_value(state, group, key)
            if actual != expected[raw_key]:
                errors.append(
                    "precondition:%s.%s:%s!=%s" % [
                        group,
                        key,
                        str(actual),
                        str(expected[raw_key])
                    ]
                )
    return errors

func _slice_events(evidence, start_index: int) -> Array:
    var all_events: Array = evidence.events()
    if start_index >= all_events.size():
        return []
    return all_events.slice(start_index, all_events.size())

func _runtime_evidence_bundle(events: Array) -> Dictionary:
    return {
        "schema": "remaster.runtime_evidence",
        "version": 1,
        "events": events
    }

func _contextualize_scenario(step: Dictionary, scenario: Dictionary) -> Dictionary:
    var runtime_scenario: Dictionary = scenario.duplicate(true)
    var metadata = step.get("metadata", {})
    if not metadata is Dictionary:
        return runtime_scenario

    var source_actions = runtime_scenario.get("actions", [])
    if not source_actions is Array:
        source_actions = []
    var skip_prefixes = metadata.get("skip_action_prefixes", [])
    if not skip_prefixes is Array:
        skip_prefixes = []
    var actions: Array = []

    var entry_actions = metadata.get("playthrough_entry_actions", [])
    if entry_actions is Array:
        for raw_entry in entry_actions:
            if raw_entry is Dictionary:
                actions.append(raw_entry.duplicate(true))

    for raw_action in source_actions:
        if not raw_action is Dictionary:
            actions.append(raw_action)
            continue
        var action_id := String(raw_action.get("action_id", ""))
        var skip := false
        for raw_prefix in skip_prefixes:
            var prefix := String(raw_prefix)
            if not prefix.is_empty() and action_id.begins_with(prefix):
                skip = true
                break
        if not skip:
            actions.append(raw_action.duplicate(true))

    runtime_scenario["actions"] = actions
    var runtime_meta = runtime_scenario.get("metadata", {})
    if not runtime_meta is Dictionary:
        runtime_meta = {}
    runtime_meta = runtime_meta.duplicate(true)
    runtime_meta["playthrough_contextualized"] = true
    runtime_meta["playthrough_entry_action_count"] = (
        entry_actions.size() if entry_actions is Array else 0
    )
    runtime_meta["playthrough_skip_action_prefixes"] = skip_prefixes.duplicate()
    runtime_scenario["metadata"] = runtime_meta
    return runtime_scenario

func _run_scenario_step(
    step: Dictionary,
    scenario: Dictionary,
    manager: Node,
    state: Node,
    evidence,
    observer,
    driver,
    navigator,
    runtime_guard
) -> Dictionary:
    var step_id := String(step.get("step_id", ""))
    var step_failures: Array[String] = []

    var expected_room := String(scenario.get("room", ""))
    var actual_room := String(manager.get("current_room_id"))
    if expected_room != actual_room:
        step_failures.append(
            "room_precondition:%s!=%s" % [actual_room, expected_room]
        )

    for error in _check_setup_preconditions(scenario, state):
        step_failures.append(error)

    var keys := _known_state_keys(scenario)
    var before_state: Dictionary = observer.snapshot_state(
        keys["inventory"],
        keys["flags"],
        keys["puzzle"]
    )

    var scene_specs = scenario.get("metadata", {}).get(
        "scene_observations",
        []
    )
    if not scene_specs is Array:
        scene_specs = []
    var scene_observer = SceneObserverScript.new(evidence)
    var scene_before: Dictionary = scene_observer.capture(
        manager.get("current_room"),
        scene_specs
    )

    var event_start: int = int(evidence.events().size())
    var executor = ActionExecutorScript.new(
        manager,
        driver,
        navigator,
        observer,
        runtime_guard
    )

    if step_failures.is_empty():
        for raw_action in scenario.get("actions", []):
            if not raw_action is Dictionary:
                step_failures.append("invalid_action_row")
                break
            var ok: bool = await executor.execute(raw_action)
            if not ok:
                for failure in executor.failure_list():
                    if not step_failures.has(failure):
                        step_failures.append(failure)
                break

    await _settle(2)
    scene_observer.emit_changes(
        manager.get("current_room"),
        scene_specs,
        scene_before
    )
    var after_state: Dictionary = observer.snapshot_state(
        keys["inventory"],
        keys["flags"],
        keys["puzzle"]
    )
    var step_events := _slice_events(evidence, event_start)

    return {
        "step_id": step_id,
        "kind": step.get("kind", ""),
        "schema": "remaster.runtime_validation_bundle",
        "version": 1,
        "scenario_id": scenario.get("scenario_id", ""),
        "status": (
            "EXECUTION_PASS"
            if step_failures.is_empty()
            else "EXECUTION_FAIL"
        ),
        "failures": step_failures,
        "scenario": scenario,
        "evidence": _runtime_evidence_bundle(step_events),
        "before_state": before_state,
        "after_state": after_state,
        "room_after": manager.get("current_room_id"),
    }

func _run_checkpoint(
    step: Dictionary,
    state: Node,
    evidence
) -> Dictionary:
    var checkpoint_id := String(step.get("checkpoint_id", ""))
    var metadata = step.get("metadata", {})
    if not metadata is Dictionary:
        metadata = {}

    var saved_payload: Array = state.call(
        "canonical_state_payload"
    ).duplicate(true)
    var before_hash := String(state.call("canonical_state_hash"))
    state.call("reset_all")
    var restore_ok := bool(
        state.call("restore_canonical_state_payload", saved_payload)
    )
    var after_hash := String(state.call("canonical_state_hash"))
    var expected_hash := String(
        metadata.get("expected_state_sha256", "")
    )
    var checkpoint_ok := (
        restore_ok
        and before_hash == after_hash
        and (
            expected_hash.is_empty()
            or after_hash == expected_hash
        )
    )

    evidence.record("save_load_checkpoint", {
        "checkpoint_id": checkpoint_id,
        "restore_ok": restore_ok,
        "before_state_sha256": before_hash,
        "after_restore_sha256": after_hash,
        "expected_state_sha256": expected_hash,
        "match": checkpoint_ok,
        "persistence_kind": "canonical_state_roundtrip"
    })

    return {
        "step_id": step.get("step_id", ""),
        "kind": "checkpoint",
        "checkpoint_id": checkpoint_id,
        "status": "PASS" if checkpoint_ok else "FAIL",
        "restore_ok": restore_ok,
        "before_state_sha256": before_hash,
        "after_restore_sha256": after_hash,
        "expected_state_sha256": expected_hash,
        "persistence_kind": "canonical_state_roundtrip"
    }

func _validate_niamh_source_fidelity(state: Node, evidence) -> Array[String]:
    var errors: Array[String] = []
    var activated := bool(state.call("flag", "R7NiamhActivated"))
    var animation_ok := false
    var conversation_ok := false
    for event in evidence.events():
        if not event is Dictionary:
            continue
        var kind := String(event.get("kind", ""))
        var payload = event.get("payload", {})
        if not payload is Dictionary:
            continue
        if kind == "character_animation_request" and String(payload.get("character", "")) == "Niamh":
            var family := String(payload.get("family", ""))
            if family == "Conv":
                errors.append("niamh_invented_conv_animation")
            if (
                family == "NOLOOP1"
                and String(payload.get("next_family", "")) == "REST"
                and String(payload.get("status", "")) == "PLAYING_SOURCE_CLIP"
            ):
                animation_ok = true
        elif kind == "conversation_request" and String(payload.get("character", "")) == "Niamh":
            if (
                String(payload.get("family", "")) == "1A"
                and String(payload.get("status", "")) == "SOURCE_TEXT_READY"
            ):
                conversation_ok = true
    if activated and not animation_ok:
        errors.append("niamh_activation_missing_source_noloop1_rest")
    if activated and not conversation_ok:
        errors.append("niamh_activation_missing_source_conversation_1a")
    return errors

func _finish(
    output_path: String,
    plan: Dictionary,
    scenario_bundle: Dictionary,
    step_results: Array,
    state: Node,
    evidence,
    scene: Node,
    runtime_guard = null
) -> void:
    if runtime_guard != null:
        for failure in runtime_guard.failure_list():
            if not failures.has(String(failure)):
                failures.append(String(failure))
    for failure in _validate_niamh_source_fidelity(state, evidence):
        if not failures.has(String(failure)):
            failures.append(String(failure))
    var final_hash := String(state.call("canonical_state_hash"))
    var expected_hash := String(plan.get("success_state_sha256", ""))
    if not expected_hash.is_empty() and final_hash != expected_hash:
        failures.append("final_state_hash_mismatch")

    for result in step_results:
        if not result is Dictionary:
            failures.append("invalid_step_result")
            continue
        var status := String(result.get("status", ""))
        if status not in ["PASS", "EXECUTION_PASS"]:
            failures.append(
                "step_failed:" + String(result.get("step_id", ""))
            )

    var payload := {
        "schema": "remaster.runtime_playthrough_bundle",
        "version": 1,
        "status": (
            "EXECUTION_PASS" if failures.is_empty() else "EXECUTION_FAIL"
        ),
        "failures": failures,
        "plan": plan,
        "scenario_bundle_schema": scenario_bundle.get("schema", ""),
        "steps": step_results,
        "final_state_sha256": final_hash,
        "expected_final_state_sha256": expected_hash,
        "evidence": evidence.bundle(),
        "runtime_guard_failures": (
            runtime_guard.failure_list() if runtime_guard != null else []
        ),
        "replay": (
            runtime_guard.replay_bundle() if runtime_guard != null else {}
        ),
        "runtime_boundary": {
            "single_scene_instance": true,
            "state_reset_between_scenarios": false,
            "direct_interact_calls": false,
            "gameplay_teleport_during_actions": false,
            "checkpoint_persistence": "canonical_state_roundtrip",
            "frame_level_avatar_trajectory": true,
            "world_state_snapshots": true,
            "softlock_watchdog": true,
            "transition_spawn_validation": true
        }
    }
    var wrote := _write_json(output_path, payload)
    if not wrote:
        push_error("OpenAzrael PPPV playthrough: cannot write " + output_path)
        failures.append("output_write_failed")

    print("OPENAZRAEL_PPPV_PLAYTHROUGH " + JSON.stringify({
        "status": payload["status"],
        "failures": failures,
        "final_state_sha256": final_hash,
        "output": output_path
    }))

    if scene != null:
        scene.queue_free()
    quit(0 if failures.is_empty() and wrote else 1)

func _run() -> void:
    proof_enabled = _arg_enabled("--pppv-proof-overlay")
    var plan_path := _arg_value("--pppv-plan=")
    var scenarios_path := _arg_value("--pppv-scenarios=")
    var output_path := _arg_value(
        "--pppv-output=",
        "user://openazrael_pppv_playthrough.json"
    )

    var plan := _load_json(plan_path)
    var scenario_bundle := _load_json(scenarios_path)
    if plan.get("schema") != "remaster.playthrough_plan":
        push_error("OpenAzrael PPPV playthrough: invalid plan")
        quit(2)
        return
    if scenario_bundle.get("schema") != "openazrael.pppv_scenario_bundle":
        push_error("OpenAzrael PPPV playthrough: invalid scenario bundle")
        quit(2)
        return
    if String(plan.get("status", "")) != "READY":
        push_error("OpenAzrael PPPV playthrough: plan is not authoring-ready")
        quit(2)
        return

    var scenarios := _scenario_map(scenario_bundle)
    var state = root.get_node_or_null("DemoState")
    var events = root.get_node_or_null("LegacyEvents")
    var diagnostics = root.get_node_or_null("CandidateDiagnostics")
    if state == null or events == null:
        push_error("OpenAzrael PPPV playthrough: required autoload missing")
        quit(2)
        return

    state.call("reset_all")

    var packed = load("res://main.tscn")
    if packed == null:
        push_error("OpenAzrael PPPV playthrough: main scene unavailable")
        quit(2)
        return
    var scene = packed.instantiate()
    root.add_child(scene)
    current_scene = scene
    await _settle(3)

    var manager = scene.get_node_or_null("RoomManager")
    var player = scene.get_node_or_null("Player")
    var probe = scene.get_node_or_null("Player/Camera3D/InteractionProbe")
    if (
        manager == null
        or not (player is CharacterBody3D)
        or probe == null
    ):
        push_error("OpenAzrael PPPV playthrough: runtime nodes unavailable")
        scene.queue_free()
        quit(2)
        return

    _proof_overlay_create()
    _proof_overlay_update({"step_id": "BOOT"}, manager, "READY")

    var evidence = EvidenceBusScript.new()
    var observer = ObserverScript.new(
        evidence,
        state,
        events,
        diagnostics
    )
    observer.attach()
    var runtime_guard = RuntimeGuardScript.new(
        player,
        manager,
        state,
        evidence
    )
    var driver = PlayerDriverScript.new(
        player,
        probe,
        evidence,
        runtime_guard
    )
    var navigator = NavigatorScript.new(
        player,
        probe,
        evidence,
        runtime_guard
    )

    var step_results: Array = []
    for raw_step in plan.get("steps", []):
        if not raw_step is Dictionary:
            failures.append("invalid_plan_step")
            break

        _proof_overlay_update(raw_step, manager, "RUNNING")
        var kind := String(raw_step.get("kind", ""))
        if kind == "checkpoint":
            var checkpoint_result := _run_checkpoint(raw_step, state, evidence)
            step_results.append(checkpoint_result)
            _proof_overlay_update(
                raw_step,
                manager,
                String(checkpoint_result.get("status", "UNKNOWN"))
            )
            continue

        var scenario_id := String(raw_step.get("scenario_id", ""))
        if scenario_id.is_empty() or not scenarios.has(scenario_id):
            failures.append(
                "scenario_missing:" + String(raw_step.get("step_id", ""))
            )
            break

        var runtime_scenario := _contextualize_scenario(
            raw_step,
            scenarios[scenario_id]
        )
        var result: Dictionary = await _run_scenario_step(
            raw_step,
            runtime_scenario,
            manager,
            state,
            evidence,
            observer,
            driver,
            navigator,
            runtime_guard
        )
        step_results.append(result)
        _proof_overlay_update(
            raw_step,
            manager,
            String(result.get("status", "UNKNOWN"))
        )
        if String(result.get("status", "")) != "EXECUTION_PASS":
            break

    _proof_overlay_update(
        {"step_id": "FINAL_STATE"},
        manager,
        "VERIFYING EVIDENCE"
    )
    _finish(
        output_path,
        plan,
        scenario_bundle,
        step_results,
        state,
        evidence,
        scene,
        runtime_guard
    )
