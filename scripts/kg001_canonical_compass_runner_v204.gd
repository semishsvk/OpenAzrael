extends SceneTree
var checks := {}
func _initialize() -> void:
    call_deferred("_run")
func _run() -> void:
    var scene = load("res://main.tscn").instantiate()
    root.add_child(scene)
    for i in range(8):
        await process_frame
    var compass = scene.get_node("LegacyMenuV145/LegacyMenuRootV145/Classic640x480/CanonicalCompassV204")
    var camera: Camera3D = scene.get_node("Player/Camera3D")
    checks["production_compass_present"] = compass != null and compass.texture != null
    checks["source_origin"] = compass.position == Vector2(146, 15)
    checks["source_size"] = compass.size == Vector2(348, 24)
    var hash_context := HashingContext.new()
    hash_context.start(HashingContext.HASH_SHA256)
    hash_context.update(compass.indexed_frame(0))
    checks["original_startup_8352_pixels_exact"] = hash_context.finish().hex_encode() == compass.source["original_startup_indices_sha256"]
    checks["heading_wrap"] = compass.indexed_frame(360) == compass.indexed_frame(0) and compass.indexed_frame(-90) == compass.indexed_frame(270)
    checks["heading_changes_pixels"] = compass.indexed_frame(90) != compass.indexed_frame(0)
    checks["nearest_sampling"] = compass.texture_filter == CanvasItem.TEXTURE_FILTER_NEAREST
    checks["does_not_capture_mouse"] = compass.mouse_filter == Control.MOUSE_FILTER_IGNORE
    checks["production_start_heading_north"] = compass.heading_degrees() == 0
    var saved := camera.global_transform
    camera.global_basis = Basis(Vector3.UP, PI / 2.0) * saved.basis
    checks["production_east_heading"] = compass.heading_degrees() == 90
    camera.global_transform = saved
    var failed := []
    for key in checks:
        if not checks[key]:
            failed.append(key)
    var result := {"schema":"openazrael.kg001.canonical_compass_runtime","version":204,"status":"PASS" if failed.is_empty() else "FAIL","checks":checks,"failed":failed,"scope":"Original indexed compass reconstruction and production integration; other graphical checkpoints separate."}
    var file := FileAccess.open("res://.tmp/kg001_c6_final_audit/canonical_compass_runtime_v204.json", FileAccess.WRITE)
    file.store_string(JSON.stringify(result,"  "))
    print("C6_COMPASS_V204 " + JSON.stringify(result))
    scene.queue_free()
    quit(0 if failed.is_empty() else 1)
