extends SceneTree

# Candidate 2 canonical-view rendering evidence.
# This is graphical observational evidence, not a cross-GPU pixel-perfect gate.

const CAPTURES := [
    {"room":"R1", "view":"spaview"},
    {"room":"R7", "view":"view"},
    {"room":"R8", "view":"Object14"},
]

var failures: Array[String] = []
var rows: Array[Dictionary] = []

func _initialize() -> void:
    call_deferred("_run")

func _check(name: String, condition: bool) -> void:
    if not condition:
        failures.append(name)

func _settle(frames: int = 4) -> void:
    for _i in range(frames):
        await process_frame

func _sha256_file(path: String) -> String:
    if not FileAccess.file_exists(path):
        return ""
    var bytes := FileAccess.get_file_as_bytes(path)
    var ctx := HashingContext.new()
    if ctx.start(HashingContext.HASH_SHA256) != OK:
        return ""
    if ctx.update(bytes) != OK:
        return ""
    return ctx.finish().hex_encode()

func _capture(viewport: Viewport, room_id: String, view_name: String) -> Dictionary:
    await RenderingServer.frame_post_draw
    var image := viewport.get_texture().get_image()
    if image == null or image.is_empty():
        return {"status":"FAIL", "room":room_id, "view":view_name, "error":"empty viewport image"}

    var capture_dir := CandidateDiagnostics.run_dir + "/captures"
    var absolute := ProjectSettings.globalize_path(capture_dir)
    var mkdir_error := DirAccess.make_dir_recursive_absolute(absolute)
    if mkdir_error != OK and mkdir_error != ERR_ALREADY_EXISTS:
        return {"status":"FAIL", "room":room_id, "view":view_name, "error":"capture mkdir failed"}

    var path := "%s/%s_%s.png" % [capture_dir, room_id, view_name]
    var save_error := image.save_png(path)
    if save_error != OK:
        return {"status":"FAIL", "room":room_id, "view":view_name, "error":"save_png failed"}

    return {
        "status":"PASS",
        "room":room_id,
        "view":view_name,
        "path":path,
        "width":image.get_width(),
        "height":image.get_height(),
        "sha256":_sha256_file(path),
    }

func _finish(scene: Node = null, code: int = 0) -> void:
    var manifest := {
        "schema":"openazrael.kg001.visual_capture",
        "version":117,
        "status":"PASS" if failures.is_empty() else "FAIL",
        "build_id":CandidateDiagnostics.BUILD_ID,
        "checkpoint":CandidateDiagnostics.BUILD_CHECKPOINT,
        "run_id":CandidateDiagnostics.run_id,
        "build_commit_sha":String(CandidateDiagnostics.build_manifest.get("commit_sha", "")),
        "rendering_method":ProjectSettings.get_setting("rendering/renderer/rendering_method", ""),
        "display_server":DisplayServer.get_name(),
        "captures":rows,
        "failed":failures,
        "oracle":"OBSERVATIONAL_CANONICAL_VIEW_NOT_CROSS_GPU_PIXEL_HASH",
    }
    if not CandidateDiagnostics.run_dir.is_empty():
        var path := CandidateDiagnostics.run_dir + "/captures/manifest.json"
        var absolute_dir := ProjectSettings.globalize_path(CandidateDiagnostics.run_dir + "/captures")
        DirAccess.make_dir_recursive_absolute(absolute_dir)
        var f := FileAccess.open(path, FileAccess.WRITE)
        if f != null:
            f.store_string(JSON.stringify(manifest, "  ") + "\n")
            f.flush()
    print("OPENAZRAEL_KG001_VISUAL_V117 " + JSON.stringify(manifest))
    if scene != null and is_instance_valid(scene):
        scene.queue_free()
    quit(code if not failures.is_empty() else 0)

func _run() -> void:
    if DisplayServer.get_name() == "headless":
        print("OPENAZRAEL_KG001_VISUAL_V117 " + JSON.stringify({
            "schema":"openazrael.kg001.visual_capture",
            "version":117,
            "status":"BLOCKED_HEADLESS",
            "oracle":"OBSERVATIONAL_CANONICAL_VIEW_NOT_CROSS_GPU_PIXEL_HASH",
        }))
        quit(2)
        return

    var required := [
        "res://assets/rooms/R1.glb",
        "res://assets/rooms/R7.glb",
        "res://assets/rooms/R8.glb",
        "res://data/generated/kg001_candidate_build_manifest.json",
    ]
    var missing: Array[String] = []
    for path in required:
        if not ResourceLoader.exists(path) and not FileAccess.file_exists(path):
            missing.append(path)
    if not missing.is_empty():
        print("OPENAZRAEL_KG001_VISUAL_V117 " + JSON.stringify({
            "schema":"openazrael.kg001.visual_capture",
            "version":117,
            "status":"BLOCKED_MISSING_ASSETS",
            "missing":missing,
        }))
        quit(2)
        return

    var packed = load("res://main.tscn")
    _check("main_scene_load", packed is PackedScene)
    if not packed is PackedScene:
        _finish(null, 1)
        return

    var scene = (packed as PackedScene).instantiate()
    root.add_child(scene)
    current_scene = scene
    await _settle(6)

    var manager = scene.get_node_or_null("RoomManager")
    var player = scene.get_node_or_null("Player")
    var hud = scene.get_node_or_null("HUD")
    var trigger_debug = scene.get_node_or_null("TriggerDebugV116")
    _check("room_manager_present", manager != null)
    _check("player_present", player is CharacterBody3D)
    if manager == null or not (player is CharacterBody3D):
        _finish(scene, 1)
        return

    if hud is CanvasLayer:
        (hud as CanvasLayer).visible = false
    if trigger_debug is Node3D:
        (trigger_debug as Node3D).visible = false

    (player as CharacterBody3D).set_physics_process(false)
    (player as CharacterBody3D).set_process_input(false)
    (player as CharacterBody3D).set_process_unhandled_input(false)
    Input.mouse_mode = Input.MOUSE_MODE_VISIBLE

    var viewport := scene.get_viewport()
    _check("viewport_present", viewport != null)
    if viewport == null:
        _finish(scene, 1)
        return

    for spec in CAPTURES:
        var room_id := String(spec["room"])
        var view_name := String(spec["view"])
        manager.call("load_room", room_id, false)
        await _settle(3)
        manager.call("_spawn_at_portal", room_id, view_name)
        manager.set("transition_cooldown", 999.0)
        (player as CharacterBody3D).velocity = Vector3.ZERO
        await _settle(4)
        var row := await _capture(viewport, room_id, view_name)
        rows.append(row)
        _check(room_id + "_capture_pass", row.get("status") == "PASS")
        if row.get("status") == "PASS":
            _check(room_id + "_capture_width", int(row.get("width", 0)) == 1280)
            _check(room_id + "_capture_height", int(row.get("height", 0)) == 720)
            _check(room_id + "_capture_sha256", String(row.get("sha256", "")).length() == 64)

    _check("capture_count", rows.size() == 3)
    CandidateDiagnostics.record_event("canonical_visual_capture", {
        "status":"PASS" if failures.is_empty() else "FAIL",
        "captures":rows,
    })
    _finish(scene, 1)
