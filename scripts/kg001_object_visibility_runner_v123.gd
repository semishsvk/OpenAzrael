extends SceneTree

const EXPECTED_HIDDEN := {
    "R1": [
        "Object03__mesh", "textwall__mesh", "zyR02__mesh", "zyR05__mesh",
        "zxentry__mesh", "zxcoriR5__mesh", "zxcoriR2__mesh"
    ],
    "R7": [
        "zxdeath__mesh", "zydeath__mesh", "death__mesh", "well_pzpa1__mesh",
        "well_pzpa2__mesh", "zyR06__mesh", "zxactghost__mesh", "zxwell2R6__mesh"
    ],
    "R8": [
        "Object01__mesh", "zxshield__mesh", "mirror03__mesh", "mirror2__mesh",
        "zxsound2__mesh", "zxsound1__mesh", "zxsound__mesh", "zxplate__mesh",
        "zyR09__mesh", "zyR06__mesh", "zxorrery__mesh", "zxsecret__mesh",
        "zxminehd__mesh", "r8s1__mesh", "lenstop__mesh", "lenstop01__mesh",
        "tapestry1__mesh", "tapestry3__mesh", "tapestry4__mesh",
        "tapestry2a__mesh"
    ],
}

const MUST_VISIBLE := {
    "R1": [
        "TONG6__mesh", "r1p1__mesh", "r3t1__mesh", "save__mesh",
        "doorcor01__mesh", "doorcor2__SPADOOR", "doorcor2__1KEYHOLE"
    ],
    "R7": [
        "nibdyky01__mesh", "nibody__mesh", "well_lev02__mesh",
        "well_weel3__mesh", "well_floor__mesh", "pipes2well__mesh"
    ],
    "R8": [
        "r8t3__mesh", "r8t4__mesh", "lens__mesh", "bible__mesh",
        "tapestry2__mesh", "zxwater__mesh", "door__mesh", "bath__BAPFLOOR"
    ],
}

const EXPECTED_MESH_COUNTS := {"R1": 69, "R7": 48, "R8": 87}

var failures: Array[String] = []
var check_count := 0
var room_summaries: Dictionary = {}
var lifecycle: Dictionary = {}

func _initialize() -> void:
    call_deferred("_run")

func _check(name: String, condition: bool) -> void:
    check_count += 1
    if not condition:
        failures.append(name)

func _settle(frames: int = 2) -> void:
    for _i in range(frames):
        await process_frame

func _walk(node: Node, out: Array[Node]) -> void:
    out.append(node)
    for child in node.get_children():
        _walk(child, out)

func _find_named(node: Node, wanted: String) -> Node:
    if String(node.name) == wanted:
        return node
    for child in node.get_children():
        var found := _find_named(child, wanted)
        if found != null:
            return found
    return null

func _mesh_visibility(root_node: Node) -> Dictionary:
    var nodes: Array[Node] = []
    _walk(root_node, nodes)
    var result := {}
    for node in nodes:
        if node is MeshInstance3D:
            var mi := node as MeshInstance3D
            if mi.mesh != null:
                result[String(mi.name)] = mi.is_visible_in_tree()
    return result

func _audit_fresh(manager, room_id: String) -> void:
    manager.load_room(room_id, false)
    await _settle(2)
    _check(room_id + "_loaded", manager.current_room != null)
    if manager.current_room == null:
        return

    var visibility := _mesh_visibility(manager.current_room)
    _check(room_id + "_mesh_count", visibility.size() == int(EXPECTED_MESH_COUNTS[room_id]))

    var actual_hidden: Array[String] = []
    for mesh_name in visibility.keys():
        if not bool(visibility[mesh_name]):
            actual_hidden.append(String(mesh_name))
    actual_hidden.sort()

    var expected_hidden: Array[String] = []
    for mesh_name in EXPECTED_HIDDEN[room_id]:
        expected_hidden.append(String(mesh_name))
    expected_hidden.sort()

    _check(room_id + "_exact_fresh_hidden_set", actual_hidden == expected_hidden)

    for mesh_name in MUST_VISIBLE[room_id]:
        _check(
            room_id + "_must_visible_" + String(mesh_name),
            visibility.has(mesh_name) and bool(visibility[mesh_name])
        )

    room_summaries[room_id] = {
        "mesh_count": visibility.size(),
        "visible_count": visibility.size() - actual_hidden.size(),
        "hidden_count": actual_hidden.size(),
        "hidden_meshes": actual_hidden,
    }

func _node_visible(manager, name: String) -> bool:
    if manager.current_room == null:
        return false
    var node := _find_named(manager.current_room, name)
    if node == null:
        return false
    if node is CanvasItem:
        return (node as CanvasItem).is_visible_in_tree()
    if node is Node3D:
        return (node as Node3D).is_visible_in_tree()
    return false

func _interact_named(manager, wanted: String) -> bool:
    if manager.current_room == null:
        return false
    var node := _find_named(manager.current_room, wanted)
    if node == null or not node.has_method("interact"):
        return false
    node.call("interact")
    return true

func _audit_lifecycle(manager, state) -> void:
    state.reset_all()
    manager.load_room("R1", false)
    await _settle(2)

    _check("fresh_tongs_visible", _node_visible(manager, "TONG6"))
    _check("fresh_parchment_visible", _node_visible(manager, "r1p1"))
    _check("fresh_tapestry_piece1_visible", _node_visible(manager, "r3t1"))

    _check("pickup_tongs", _interact_named(manager, "Interact_TONG6"))
    _check("pickup_parchment", _interact_named(manager, "Interact_r1p1"))
    _check("pickup_tapestry_piece1", _interact_named(manager, "Interact_r3t1"))
    await _settle(2)
    _check("tongs_hidden_after_pickup", not _node_visible(manager, "TONG6"))
    _check("parchment_hidden_after_pickup", not _node_visible(manager, "r1p1"))
    _check("piece1_hidden_after_pickup", not _node_visible(manager, "r3t1"))

    # Use the production R7 interaction so TONG6 leaves inventory according to
    # the recovered source action group; then R1 reload must not resurrect it.
    manager.load_room("R7", false)
    await _settle(2)
    _check("well_key_initially_visible", _node_visible(manager, "nibdyky01"))
    _check("well_key_interaction", _interact_named(manager, "Interact_WellKey"))
    await _settle(2)
    _check("well_key_hidden_after_take", not _node_visible(manager, "nibdyky01"))
    _check("tongs_consumed_from_inventory", not state.has("rusty_tongs"))
    _check("r7key_source_flag", state.flag("R7key"))

    manager.load_room("R1", false)
    await _settle(2)
    _check("tongs_no_respawn_after_consumption", not _node_visible(manager, "TONG6"))
    _check("tongs_interaction_no_respawn", _find_named(manager.current_room, "Interact_TONG6") == null)
    _check("parchment_no_respawn_while_held", not _node_visible(manager, "r1p1"))

    # Piece 1 moves from its loose R1 object to the authored R8 tapestry mesh.
    manager.load_room("R8", false)
    await _settle(2)
    _check("piece1_installed_initially_hidden", not _node_visible(manager, "tapestry1"))
    _check("frame1_place", _interact_named(manager, "Interact_tapframe1"))
    await _settle(2)
    _check("piece1_inventory_consumed", not state.has("tapestry_piece_1"))
    _check("piece1_installed_visible", _node_visible(manager, "tapestry1"))
    _check("piece1_source_flag", state.flag("R8Tap1"))

    manager.load_room("R1", false)
    await _settle(2)
    _check("piece1_loose_no_respawn_after_placement", not _node_visible(manager, "r3t1"))
    _check("piece1_interaction_no_respawn", _find_named(manager.current_room, "Interact_r3t1") == null)

    # R8 loose pieces 3/4 have the same persistence rule.
    manager.load_room("R8", false)
    await _settle(2)
    _check("fresh_piece3_visible", _node_visible(manager, "r8t3"))
    _check("fresh_piece4_visible", _node_visible(manager, "r8t4"))
    _check("pickup_piece3", _interact_named(manager, "Interact_r8t3"))
    _check("pickup_piece4", _interact_named(manager, "Interact_r8t4"))
    await _settle(2)
    _check("frame3_place", _interact_named(manager, "Interact_tapframe3"))
    _check("frame4_place", _interact_named(manager, "Interact_tapframe4"))
    await _settle(2)
    _check("installed_piece3_visible", _node_visible(manager, "tapestry3"))
    _check("installed_piece4_visible", _node_visible(manager, "tapestry4"))

    manager.load_room("R8", false)
    await _settle(2)
    _check("piece3_loose_no_respawn", not _node_visible(manager, "r8t3"))
    _check("piece4_loose_no_respawn", not _node_visible(manager, "r8t4"))
    _check("piece3_installed_persists", _node_visible(manager, "tapestry3"))
    _check("piece4_installed_persists", _node_visible(manager, "tapestry4"))

    # R8 authored state-dependent visuals.
    state.reset_all()
    manager.load_room("R8", false)
    await _settle(2)
    _check("water_visible_before_drain", _node_visible(manager, "zxwater"))
    _check("lens_visible_before_retrieval", _node_visible(manager, "lens"))
    _check("bible_visible_fresh", _node_visible(manager, "bible"))
    _check("shield_hidden_before_door", not _node_visible(manager, "r8s1"))
    _check("message_hidden_before_rotate", not _node_visible(manager, "tapestry2a"))

    state.set_flag("R8BathDrain")
    manager.load_room("R8", false)
    await _settle(2)
    _check("water_hidden_after_drain", not _node_visible(manager, "zxwater"))
    _check("lens_still_visible_after_drain", _node_visible(manager, "lens"))
    _check("lens_take", _interact_named(manager, "Interact_R8Lens"))
    await _settle(2)
    _check("lens_hidden_after_take", not _node_visible(manager, "lens"))

    var bible_area := _find_named(manager.current_room, "Interact_R8Bible")
    _check("bible_interaction_present", bible_area != null and bible_area.has_method("interact"))
    if bible_area != null and bible_area.has_method("interact"):
        bible_area.call("interact")
    await _settle(2)
    _check("installed_lens_visible_after_place", _node_visible(manager, "lenstop"))
    _check("loose_lens_hidden_after_place", not _node_visible(manager, "lens"))

    state.set_puzzle_node("DoorR8")
    manager.load_room("R8", false)
    await _settle(2)
    _check("shield_visible_after_door", _node_visible(manager, "r8s1"))
    state.set_flag("demo_complete")
    manager.load_room("R8", false)
    await _settle(2)
    _check("shield_hidden_after_demo_complete", not _node_visible(manager, "r8s1"))

    state.reset_all()
    manager.load_room("R8", false)
    await _settle(2)
    _check("rotate_tapestry", _interact_named(manager, "Interact_R8Tapestry2"))
    await _settle(2)
    _check("message_visible_after_rotate", _node_visible(manager, "tapestry2a"))

    lifecycle = {
        "tongs_no_respawn": state != null,
        "parchment_pickup_checked": true,
        "tapestry_piece_persistence_checked": true,
        "r8_water_lens_shield_message_checked": true,
    }

func _finish(scene: Node = null) -> void:
    var result := {
        "schema": "openazrael.kg001.object_visibility_parity",
        "version": 123,
        "status": "PASS" if failures.is_empty() else "FAIL",
        "checks": check_count,
        "failed": failures,
        "fresh_rooms": room_summaries,
        "lifecycle": lifecycle,
        "policy": "exact source-authored visible/hidden object state; no silent disappearing objects and no consumed-pickup respawn",
    }
    print("OPENAZRAEL_KG001_OBJECT_VISIBILITY_V123 " + JSON.stringify(result))
    if scene != null:
        scene.queue_free()
    quit(0 if failures.is_empty() else 1)

func _run() -> void:
    for path in [
        "res://assets/rooms/R1.glb",
        "res://assets/rooms/R7.glb",
        "res://assets/rooms/R8.glb",
    ]:
        if not ResourceLoader.exists(path):
            print("OPENAZRAEL_KG001_OBJECT_VISIBILITY_V123 " + JSON.stringify({
                "schema": "openazrael.kg001.object_visibility_parity",
                "version": 123,
                "status": "BLOCKED_MISSING_ASSETS",
                "missing": path,
            }))
            quit(2)
            return

    var state = root.get_node_or_null("DemoState")
    _check("demo_state_present", state != null)
    if state == null:
        _finish()
        return
    state.reset_all()

    var packed = load("res://main.tscn")
    _check("main_scene_load", packed is PackedScene)
    if not packed is PackedScene:
        _finish()
        return

    var scene = packed.instantiate()
    root.add_child(scene)
    await _settle(3)
    var manager = scene.get_node_or_null("RoomManager")
    _check("room_manager_present", manager != null)
    if manager == null:
        _finish(scene)
        return

    for room_id in ["R1", "R7", "R8"]:
        state.reset_all()
        await _audit_fresh(manager, room_id)

    await _audit_lifecycle(manager, state)
    _finish(scene)
