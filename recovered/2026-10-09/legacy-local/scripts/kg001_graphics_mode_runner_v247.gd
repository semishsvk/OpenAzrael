extends SceneTree
var failed: Array[String] = []
var checks := 0
var graphics: Node

func check(name: String, ok: bool) -> void:
    checks += 1
    if not ok:
        failed.append(name)

func _initialize() -> void:
    call_deferred("_run")

func _run() -> void:
    graphics = root.get_node_or_null("GraphicsMode")
    check("graphics_autoload", graphics != null)
    if graphics == null:
        finish()
        return
    check("manifest_ok", bool(graphics.call("manifest_ok")))
    check("variant_count_89", int(graphics.call("variant_count")) == 89)
    var packed = load("res://main.tscn")
    check("main", packed is PackedScene)
    if not packed is PackedScene:
        finish()
        return
    graphics.call("set_mode", 0)
    var scene = packed.instantiate()
    root.add_child(scene)
    for _i in range(6):
        await process_frame
    var rm = scene.get_node("RoomManager")
    check("classic_mode", String(graphics.call("mode_name")) == "CLASSIC")
    for id in ["R1", "R7", "R8"]:
        rm.load_room(id, false)
        await process_frame
        var classic_overrides := 0
        for n in rm.current_room.find_children("*", "MeshInstance3D", true, false):
            var mi := n as MeshInstance3D
            if mi == null or mi.mesh == null:
                continue
            for s in range(mi.mesh.get_surface_count()):
                var m = mi.get_surface_override_material(s) as StandardMaterial3D
                if m != null and m.albedo_texture != null and "assets/upscaled4x/" in m.albedo_texture.resource_path:
                    classic_overrides += 1
        check("classic_" + id, classic_overrides == 0)
    graphics.call("set_mode", 1)
    for id in ["R1", "R7", "R8"]:
        rm.load_room(id, false)
        for _i in range(3):
            await process_frame
        var count := 0
        for n in rm.current_room.find_children("*", "MeshInstance3D", true, false):
            var mi := n as MeshInstance3D
            if mi == null or mi.mesh == null:
                continue
            for s in range(mi.mesh.get_surface_count()):
                var m = mi.get_surface_override_material(s) as StandardMaterial3D
                if m != null and m.albedo_texture != null and "assets/upscaled4x/" in m.albedo_texture.resource_path:
                    count += 1
        check("upscaled_" + id, count > 0)
    graphics.call("set_mode", 2)
    check("reserved_falls_back_classic", String(graphics.call("mode_name")) == "CLASSIC")
    scene.queue_free()
    await process_frame
    finish()

func finish() -> void:
    var count := int(graphics.call("variant_count")) if graphics != null else 0
    var out = {"schema":"openazrael.graphics_mode_runtime","version":247,"checks":checks,"failed":failed,"variant_count":count,"status":"PASS" if failed.is_empty() else "FAIL"}
    print("OPENAZRAEL_GRAPHICS_MODE_V247 " + JSON.stringify(out))
    quit(0 if failed.is_empty() else 1)
