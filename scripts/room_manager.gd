extends Node3D

signal room_changed(room_id: String)

const ROOM_SCENE_PATHS := {
    "R1": "res://assets/rooms/R1.glb",
    "R7": "res://assets/rooms/R7.glb",
    "R8": "res://assets/rooms/R8.glb"
}
const ROOM_NAMES := {
    "R1":"Entry Corridor (R1)",
    "R7":"Well Room (R7)",
    "R8":"Baptistery (R8)"
}
const PORTAL_SPAWN_CLEARANCE := 4.0
const PORTAL_SPAWN_DISTANCE := 120.0
const PORTAL_SPAWN_DISTANCE_CANDIDATES := [120.0, 115.0, 125.0, 110.0, 130.0, 105.0, 135.0, 100.0]
const PORTAL_SUPPORT_RAY_UP := 8.0
const PORTAL_SUPPORT_RAY_DOWN := 48.0
const PORTAL_SUPPORT_CLEARANCE := 0.2
const TRIGGER_EVENT_IR_PATH := "res://data/trigger_event_ir_v137.json"

const PICKUPS := {
    "R1": {
        "TONG6": ["rusty_tongs", "Tongs"],
        "r1p1": ["parchment_r1", "Parchment"],
        "r3t1": ["tapestry_piece_1", "Tapestry piece 1"]
    },
    "R8": {
        "r8t3": ["tapestry_piece_3", "Tapestry piece 3"],
        "r8t4": ["tapestry_piece_4", "Tapestry piece 4"]
    }
}
# Source-state flags that prove a loose pickup has already left its authored
# room location even if the inventory item was later consumed/placed.
# This prevents room reload from resurrecting TONG6 or tapestry pieces.
const PICKUP_REMOVED_BY_FLAG := {
    "TONG6": "R7key",
    "r3t1": "R8Tap1",
    "r8t3": "R8Tap3",
    "r8t4": "R8Tap4",
}

var current_room_id := "R1"
var current_room: Node3D
var evidence: Dictionary = {}
var trigger_event_ir: Dictionary = {}
var transition_cooldown := 0.0
var legacy_audio: Node3D
var _diagnostic_inside: Dictionary = {}
var _trigger_hold_reported: Dictionary = {}
var _character_animation_status: Dictionary = {}
@onready var player = get_node("../Player")

func _ready() -> void:
    legacy_audio = Node3D.new()
    legacy_audio.name = "LegacyAmbientAudio"
    legacy_audio.set_script(preload("res://scripts/legacy_ambient_audio.gd"))
    add_child(legacy_audio)

    var parsed_evidence = JSON.parse_string(FileAccess.get_file_as_string("res://data/xaf_trigger_evidence.json"))
    if not parsed_evidence is Dictionary:
        evidence = {}
        push_error("OpenAzrael KG-001 Candidate 1: invalid xaf_trigger_evidence.json")
        CandidateDiagnostics.record_event("startup_evidence_parse", {"status":"FAIL"})
        get_tree().quit(2)
        return
    evidence = parsed_evidence

    var parsed_trigger_ir = JSON.parse_string(FileAccess.get_file_as_string(TRIGGER_EVENT_IR_PATH))
    if not parsed_trigger_ir is Dictionary:
        trigger_event_ir = {}
        push_error("OpenAzrael v137: invalid trigger_event_ir_v137.json")
        CandidateDiagnostics.record_event("startup_trigger_event_ir_parse", {"status":"FAIL"})
        get_tree().quit(2)
        return
    trigger_event_ir = parsed_trigger_ir
    if not LegacyEvents.character_animation_requested.is_connected(_on_character_animation_requested):
        LegacyEvents.character_animation_requested.connect(_on_character_animation_requested)
    if not LegacyEvents.conversation_requested.is_connected(_on_conversation_requested):
        LegacyEvents.conversation_requested.connect(_on_conversation_requested)

    var require_candidate_audio := DisplayServer.get_name() != "headless"
    if not CandidateDiagnostics.fail_fast_if_required_resources_missing(require_candidate_audio):
        set_process(false)
        get_tree().quit(2)
        return

    load_room("R1", false)
    CandidateMusic.bind_room_manager(self)
    if not is_instance_valid(current_room):
        get_tree().quit(2)
        return
    _spawn_at_portal("R1", "spaview")
    transition_cooldown = 1.0

func _walk(node: Node, out: Array[Node]) -> void:
    out.append(node)
    for c in node.get_children():
        _walk(c, out)

func _find_node(name: String) -> Node3D:
    if not is_instance_valid(current_room):
        return null
    var nodes: Array[Node] = []
    _walk(current_room, nodes)
    for n in nodes:
        if n is Node3D and String(n.name) == name:
            return n as Node3D
    return null

func _first_mesh(root: Node) -> MeshInstance3D:
    if root is MeshInstance3D:
        return root as MeshInstance3D
    for c in root.get_children():
        var m := _first_mesh(c)
        if m != null:
            return m
    return null

func _object_name_for_mesh(mi: MeshInstance3D) -> String:
    var p := mi.get_parent()
    return String(p.name) if p != null else String(mi.name)

func _node_global_bounds(root: Node3D) -> AABB:
    var nodes: Array[Node] = []
    _walk(root, nodes)
    var have := false
    var mn := Vector3.ZERO
    var mx := Vector3.ZERO
    for n in nodes:
        if not (n is MeshInstance3D):
            continue
        var mi := n as MeshInstance3D
        if mi.mesh == null:
            continue
        var a := mi.get_aabb()
        for x in [a.position.x, a.end.x]:
            for y in [a.position.y, a.end.y]:
                for z in [a.position.z, a.end.z]:
                    var q := mi.to_global(Vector3(x,y,z))
                    if not have:
                        mn = q; mx = q; have = true
                    else:
                        mn = mn.min(q); mx = mx.max(q)
    return AABB(mn, mx - mn) if have else AABB(root.global_position, Vector3.ONE)

func _transparent_trigger_names(room_id: String) -> Dictionary:
    var out := {}
    if evidence.has("rooms") and evidence["rooms"].has(room_id):
        for t in evidence["rooms"][room_id]["triggers"]:
            # Both legacy helper materials are non-rendered source semantics.
            # CLEAR_OBJECT occurs on R7 well helper planes; rendering them as
            # fallback white geometry would be a fidelity bug.
            if String(t.get("material", "")) in ["TRANSPARANT", "CLEAR_OBJECT"]:
                out[String(t["name"])] = true
    return out

func _create_world_collision(room_id: String) -> void:
    var hidden := _transparent_trigger_names(room_id)
    var pickup_names: Dictionary = PICKUPS.get(room_id, {})
    var nodes: Array[Node] = []
    _walk(current_room, nodes)
    for n in nodes:
        if not (n is MeshInstance3D):
            continue
        var mi := n as MeshInstance3D
        # Legacy XAF diffuse materials have no authored PBR metalness. The
        # SimpleMaterial GLB conversion otherwise inherits glTF metallic=1,
        # which can render the imported room nearly black.
        if mi.mesh != null:
            for surface in range(mi.mesh.get_surface_count()):
                var imported := mi.get_active_material(surface) as BaseMaterial3D
                if imported != null:
                    imported.metallic = 0.0
        var obj_name := _object_name_for_mesh(mi)
        if hidden.has(obj_name):
            mi.visible = false
            # R8/Object01 is the authored horizontal entrance support quad
            # (y=-87.124, between tunnel07 and step011). Hiding its TRANSPARANT
            # material must not remove its collision: the portal spawn lies on
            # this otherwise open gap. Its diagnostic trigger remains unchanged.
            if not (room_id == "R8" and obj_name == "Object01"):
                continue
        if pickup_names.has(obj_name):
            continue
        # Collision exclusions are room-aware. Candidate 3 bug report
        # openazrael_bugreport_1790007921_0054 proved that R1/Object02 is a
        # visible authored floor segment under zxcoriR5 (player X/Z
        # -264.159/381.168) and must collide. Other rooms may contain helper
        # objects with the same generic Object02 name, so do not globally
        # re-enable every Object02.
        var exclude_collision := (
            obj_name.begins_with("ZQ")
            or obj_name in ["Object03", "view", "spaview", "entcori", "Object14", "zxwater", "tapestry1", "tapestry3", "tapestry4"]
            or (obj_name == "Object02" and room_id != "R1")
        )
        if exclude_collision:
            continue
        if mi.mesh == null:
            continue
        var shape := mi.mesh.create_trimesh_shape()
        if shape == null:
            continue
        # Legacy XAF/GLB triangle winding is not guaranteed to face the playable
        # side consistently. Concave room collision must therefore accept both
        # faces or floors can become non-colliding from above.
        if shape is ConcavePolygonShape3D:
            (shape as ConcavePolygonShape3D).backface_collision = true
        var body := StaticBody3D.new()
        body.name = "Collision_" + obj_name
        body.collision_layer = 1
        body.collision_mask = 4
        var cs := CollisionShape3D.new()
        cs.shape = shape
        body.add_child(cs)
        mi.add_child(body)

func _add_area_for_object(obj: Node3D, radius_min: float = 10.0) -> Area3D:
    var area := Area3D.new()
    area.collision_layer = 2
    area.collision_mask = 0
    var cs := CollisionShape3D.new()
    var sphere := SphereShape3D.new()
    var bounds := _node_global_bounds(obj)
    sphere.radius = max(radius_min, max(bounds.size.x, max(bounds.size.y, bounds.size.z)) * 0.55)
    cs.shape = sphere
    area.add_child(cs)
    current_room.add_child(area)
    area.global_position = bounds.get_center()
    return area

func _setup_pickups(room_id: String) -> void:
    if not PICKUPS.has(room_id):
        return
    var pickup_script = preload("res://scripts/pickup.gd")
    for object_name in PICKUPS[room_id].keys():
        var spec: Array = PICKUPS[room_id][object_name]
        var item_id := String(spec[0])
        var obj := _find_node(object_name)
        if obj == null:
            push_warning("OpenAzrael pickup object not found: " + object_name)
            continue
        var removed_flag := String(PICKUP_REMOVED_BY_FLAG.get(object_name, ""))
        var removed_from_authored_location := (
            DemoState.has(item_id)
            or (not removed_flag.is_empty() and DemoState.flag(removed_flag))
        )
        if removed_from_authored_location:
            obj.visible = false
            continue
        obj.visible = true
        var area := _add_area_for_object(obj)
        area.name = "Interact_" + object_name
        area.set_script(pickup_script)
        area.set("item_id", item_id)
        area.set("display_name", String(spec[1]))
        area.set("visual_node", obj)

func _setup_well_key() -> void:
    if current_room_id != "R7":
        return
    var key := _find_node("nibdyky01")
    if key == null:
        push_warning("OpenAzrael R7 key object nibdyky01 not found")
        return
    if DemoState.has("well_key") or DemoState.flag("R7key"):
        key.visible = false
        return
    key.visible = true
    var area := _add_area_for_object(key, 18.0)
    area.name = "Interact_WellKey"
    area.set_script(preload("res://scripts/well_key_interaction.gd"))
    area.set("key_visual", key)

func _setup_r7_character_state() -> void:
    if current_room_id != "R7":
        return
    var niamh_body := _find_node("nibody")
    if niamh_body == null:
        push_warning("OpenAzrael v137: R7 Niamh body object nibody not found")
        return
    # The source-backed zxactghost binding controls Niamh activation. Do not
    # invent a fade/motion before the original character ANI is available.
    niamh_body.visible = DemoState.flag("R7NiamhActivated")

func _collect_animation_players(root: Node, out: Array[AnimationPlayer]) -> void:
    if root is AnimationPlayer:
        out.append(root as AnimationPlayer)
    for child in root.get_children():
        _collect_animation_players(child, out)

func _on_character_animation_requested(request: Dictionary) -> void:
    var character := String(request.get("character", ""))
    var family := String(request.get("family", ""))
    var target_name := String(request.get("target_object", ""))
    var target := _find_node(target_name) if not target_name.is_empty() else null
    if target != null:
        target.visible = true

    var result := {
        "room": current_room_id,
        "character": character,
        "family": family,
        "target_object": target_name,
        "status": "HOLD_SOURCE_CLIP_MISSING"
    }
    var players: Array[AnimationPlayer] = []
    if is_instance_valid(current_room):
        _collect_animation_players(current_room, players)
    for animation_player in players:
        if animation_player.has_animation(StringName(family)):
            animation_player.play(StringName(family))
            result["status"] = "PLAYING_SOURCE_CLIP"
            result["animation_player"] = String(animation_player.get_path())
            break
    _character_animation_status[character] = result
    CandidateDiagnostics.record_event("character_animation_request", result)
    if result["status"] != "PLAYING_SOURCE_CLIP" and bool(request.get("source_required", false)):
        push_warning(
            "OpenAzrael v137: source animation clip '%s' for %s is not restored/imported; no fallback animation will be synthesized."
            % [family, character]
        )

func _on_conversation_requested(request: Dictionary) -> void:
    # Conversation dispatch is explicit even while the exact trigger-associated
    # line remains HOLD. Never substitute a remembered or guessed line.
    CandidateDiagnostics.record_event("conversation_request", {
        "room": current_room_id,
        "character": String(request.get("character", "")),
        "family": String(request.get("family", "")),
        "source_required": bool(request.get("source_required", false)),
        "status": "HOLD_EXACT_TRIGGER_LINE"
    })

func character_animation_status(character: String) -> Dictionary:
    return _character_animation_status.get(character, {}).duplicate(true)

func _setup_r7_switchboard() -> void:
    if current_room_id != "R7":
        return
    var script = preload("res://scripts/r7_switch_control.gd")
    for object_name in ["well_lev02", "well_weel3"]:
        var obj := _find_node(object_name)
        if obj == null:
            push_warning("OpenAzrael R7 switch control not found: " + object_name)
            continue
        var area := _add_area_for_object(obj, 16.0)
        area.name = "Interact_" + object_name
        area.set_script(script)
        area.set("control_id", object_name)
        area.set("visual_node", obj)

func _setup_r1_doors() -> void:
    if current_room_id != "R1":
        return
    var door_script = preload("res://scripts/r1_door_interaction.gd")
    var specs := [
        {"name":"doorcor01", "id":1, "angle":90.0},
        {"name":"doorcor2",  "id":2, "angle":-90.0}
    ]
    for spec in specs:
        var door := _find_node(String(spec["name"]))
        if door == null:
            push_warning("OpenAzrael door object not found: " + String(spec["name"]))
            continue
        var bounds := _node_global_bounds(door)
        var area := Area3D.new()
        area.name = "Interact_" + String(spec["name"])
        area.collision_layer = 2
        area.collision_mask = 0
        area.set_script(door_script)
        area.set("door_visual", door)
        area.set("door_id", int(spec["id"]))
        area.set("open_angle_degrees", float(spec["angle"]))
        var cs := CollisionShape3D.new()
        var sphere := SphereShape3D.new()
        sphere.radius = max(28.0, bounds.size.length() * 0.42)
        cs.shape = sphere
        area.add_child(cs)
        current_room.add_child(area)
        area.global_position = bounds.get_center()
        area.call("sync_from_state")

func _setup_r8() -> void:
    if current_room_id != "R8":
        return
    var water := _find_node("zxwater")
    if water != null:
        water.visible = not DemoState.flag("R8BathDrain")

    var lens := _find_node("lens")
    if lens != null:
        if DemoState.has("r8_lens") or DemoState.puzzle_node("R8LensPlace"):
            lens.visible = false
        else:
            lens.visible = true
            var lens_area := _add_area_for_object(lens, 15.0)
            lens_area.name = "Interact_R8Lens"
            lens_area.set_script(preload("res://scripts/r8_lens_interaction.gd"))
            lens_area.set("lens_visual", lens)

    var bible := _find_node("bible")
    var installed_lens := _find_node("lenstop")
    var look_lens := _find_node("lenstop01")
    var activation_zone := _find_node("zxplate")
    var door := _find_node("door")
    var shield := _find_node("r8s1")

    if installed_lens != null:
        installed_lens.visible = DemoState.puzzle_node("R8LensPlace")
    if look_lens != null:
        look_lens.visible = false
    if installed_lens != null and look_lens != null and DemoState.puzzle_node("R8LensLook"):
        installed_lens.global_transform = look_lens.global_transform

    if door != null and DemoState.puzzle_node("DoorR8"):
        door.rotation.y += deg_to_rad(90.0)

    var shield_area: Area3D = null
    if shield != null:
        shield.visible = DemoState.puzzle_node("DoorR8") and not DemoState.flag("demo_complete")
        shield_area = _add_area_for_object(shield, 22.0)
        shield_area.name = "Interact_ShieldR8"
        shield_area.set_script(preload("res://scripts/r8_shield_interaction.gd"))
        shield_area.set("shield_visual", shield)
        # Hidden Shield must not occlude the production interaction ray.
        # Its Area3D becomes active only when the source-backed DoorR8 state
        # exposes the Shield.
        shield_area.collision_layer = 2 if shield.visible else 0

    if bible != null and activation_zone != null:
        var barea := _add_area_for_object(bible, 20.0)
        barea.name = "Interact_R8Bible"
        barea.set_script(preload("res://scripts/r8_bible_interaction.gd"))
        barea.set("bible_visual", bible)
        barea.set("installed_lens_visual", installed_lens)
        barea.set("look_lens_visual", look_lens)
        barea.set("player", player)
        var zbox := _node_global_bounds(activation_zone)
        barea.set("activation_center", zbox.get_center())
        barea.set("activation_half_extents", Vector3(max(1.0, zbox.size.x * 0.5), 80.0, max(1.0, zbox.size.z * 0.5)))
        barea.set("door_visual", door)
        barea.set("shield_visual", shield)
        barea.set("shield_interaction", shield_area if shield != null else null)

    var tapestry := _find_node("tapestry2")
    var message := _find_node("tapestry2a")
    if tapestry != null:
        if message != null and not DemoState.puzzle_node("R8TapestryBack"):
            message.visible = false
        var tarea := _add_area_for_object(tapestry, 28.0)
        tarea.name = "Interact_R8Tapestry2"
        tarea.set_script(preload("res://scripts/r8_tapestry_interaction.gd"))
        tarea.set("tapestry_visual", tapestry)
        tarea.set("message_visual", message)
        tarea.call("sync_from_state")

    var frame_script = preload("res://scripts/r8_tapestry_frame.gd")
    var frame_specs := [
        {"frame":"tapframe1", "piece":"tapestry1", "item":"tapestry_piece_1", "flag":"R8Tap1"},
        {"frame":"tapframe3", "piece":"tapestry3", "item":"tapestry_piece_3", "flag":"R8Tap3"},
        {"frame":"tapframe4", "piece":"tapestry4", "item":"tapestry_piece_4", "flag":"R8Tap4"}
    ]
    for spec in frame_specs:
        var frame := _find_node(String(spec["frame"]))
        var piece := _find_node(String(spec["piece"]))
        if frame == null or piece == null:
            push_warning("OpenAzrael tapestry frame/piece missing: " + String(spec))
            continue
        var farea := _add_area_for_object(frame, 22.0)
        farea.name = "Interact_" + String(spec["frame"])
        farea.set_script(frame_script)
        farea.set("required_item", String(spec["item"]))
        farea.set("state_flag", String(spec["flag"]))
        farea.set("piece_visual", piece)
        farea.set("frame_visual", frame)
        farea.call("sync_from_state")

func load_room(id: String, announce := true) -> void:
    if not ROOM_SCENE_PATHS.has(id):
        push_error("OpenAzrael unknown room id: " + id)
        return
    var packed = load(String(ROOM_SCENE_PATHS[id]))
    if not packed is PackedScene:
        push_error("OpenAzrael KG-001 Candidate 1 cannot load room: " + String(ROOM_SCENE_PATHS[id]))
        CandidateDiagnostics.record_event("room_load_failed", {"room": id, "path": ROOM_SCENE_PATHS[id]})
        return
    if is_instance_valid(current_room):
        current_room.queue_free()
    current_room = packed.instantiate()
    current_room.name = ROOM_NAMES[id]
    add_child(current_room)
    current_room_id = id
    _diagnostic_inside.clear()
    _trigger_hold_reported.clear()
    _character_animation_status.clear()
    _create_world_collision(id)
    _setup_pickups(id)
    _setup_well_key()
    _setup_r7_character_state()
    _setup_r7_switchboard()
    _setup_r1_doors()
    _setup_r8()
    if is_instance_valid(legacy_audio):
        legacy_audio.call("setup_for_room", id)
    CandidateDiagnostics.record_room_loaded(id)
    room_changed.emit(id)
    if announce:
        print("OpenAzrael room: ", ROOM_NAMES[id])

func _v3(a: Array) -> Vector3:
    return Vector3(float(a[0]), float(a[1]), float(a[2]))

func _view_record(room_id: String, view_name: String) -> Dictionary:
    for v in evidence["rooms"][room_id]["portal_views"]:
        if v["name"] == view_name:
            return v
    return {}

func _trigger_record(room_id: String, trigger_name: String) -> Dictionary:
    for t in evidence["rooms"][room_id]["triggers"]:
        if t["name"] == trigger_name:
            return t
    return {}

func _portal_spawn_distance(c: Vector3, n: Vector3) -> float:
    var collision_shape := player.get_node_or_null("CollisionShape3D") as CollisionShape3D
    if collision_shape == null or collision_shape.shape == null:
        return PORTAL_SPAWN_DISTANCE

    var nominal_foot_y := c.y + PORTAL_SPAWN_CLEARANCE - float(player.eye_height)
    var space := get_world_3d().direct_space_state
    for distance in PORTAL_SPAWN_DISTANCE_CANDIDATES:
        var xz := c + n * float(distance)
        var floor_query := PhysicsRayQueryParameters3D.create(
            Vector3(xz.x, nominal_foot_y + PORTAL_SUPPORT_RAY_UP, xz.z),
            Vector3(xz.x, nominal_foot_y - PORTAL_SUPPORT_RAY_DOWN, xz.z),
            int(player.collision_mask)
        )
        floor_query.hit_back_faces = true
        var floor_hit := space.intersect_ray(floor_query)
        if floor_hit.is_empty():
            continue
        var floor_normal := floor_hit.get("normal", Vector3.ZERO) as Vector3
        if absf(floor_normal.y) < cos(float(player.floor_max_angle)):
            continue

        # Evaluate the capsule at its eventual floor-resting transform. Contact
        # with the supporting floor itself is acceptable; overlap with a
        # different collision body means the nominal portal spawn is perched on
        # or penetrating nearby geometry (R8/Object14 exposed this on step011).
        var floor_position := floor_hit.get("position", Vector3.ZERO) as Vector3
        var shape_query := PhysicsShapeQueryParameters3D.new()
        shape_query.shape = collision_shape.shape
        shape_query.collision_mask = int(player.collision_mask)
        shape_query.transform = Transform3D(
            Basis.IDENTITY,
            Vector3(
                xz.x,
                floor_position.y + PORTAL_SUPPORT_CLEARANCE + collision_shape.position.y,
                xz.z
            )
        )
        var support_collider = floor_hit.get("collider")
        var blocked := false
        for row in space.intersect_shape(shape_query, 16):
            if not (row is Dictionary):
                continue
            if row.get("collider") != support_collider:
                blocked = true
                break
        if not blocked:
            return float(distance)

    return PORTAL_SPAWN_DISTANCE

func _spawn_at_portal(room_id: String, view_name: String) -> void:
    var v := _view_record(room_id, view_name)
    if v.is_empty():
        return
    var c := _v3(v["centroid"])
    var n := _v3(v["normal"]).normalized()
    # The portal-view centroid is an eye-space reconstruction. Keep its authored
    # heading/Y, but choose the nearest deterministic normal offset whose
    # eventual capsule resting pose is not blocked by adjacent geometry.
    var spawn_distance := _portal_spawn_distance(c, n)
    player.teleport_eye_to(
        c + n * spawn_distance + Vector3.UP * PORTAL_SPAWN_CLEARANCE,
        n
    )

func _inside_trigger(p: Vector3, t: Dictionary) -> bool:
    var mn := _v3(t["bounds"][0])
    var mx := _v3(t["bounds"][1])
    var y0: float = min(mn.y, mx.y) - 12.0
    var y1: float = max(mn.y, mx.y) + 70.0
    return p.x >= min(mn.x,mx.x) and p.x <= max(mn.x,mx.x) \
        and p.z >= min(mn.z,mx.z) and p.z <= max(mn.z,mx.z) \
        and p.y >= y0 and p.y <= y1

func _trigger_binding(room_id: String, trigger_name: String) -> Dictionary:
    if trigger_event_ir.is_empty() or not trigger_event_ir.has("rooms"):
        return {}
    var rooms: Dictionary = trigger_event_ir["rooms"]
    if not rooms.has(room_id):
        return {}
    for binding in rooms[room_id]:
        if String(binding.get("trigger", "")) == trigger_name:
            return binding
    return {}

func _dispatch_trigger_edge(trigger_name: String, entered: bool) -> void:
    var binding := _trigger_binding(current_room_id, trigger_name)
    if binding.is_empty():
        push_error("OpenAzrael v137: unclassified authored trigger %s/%s" % [current_room_id, trigger_name])
        CandidateDiagnostics.record_event("trigger_event_unclassified", {
            "room": current_room_id,
            "trigger": trigger_name,
            "entered": entered
        })
        return

    var trigger_class := String(binding.get("class", "UNKNOWN_HOLD"))
    if trigger_class == "activation_enter" and entered:
        var one_shot_flag := String(binding.get("one_shot_flag", ""))
        if not one_shot_flag.is_empty() and DemoState.flag(one_shot_flag):
            CandidateDiagnostics.record_event("trigger_event_suppressed", {
                "room": current_room_id,
                "trigger": trigger_name,
                "reason": "one_shot_already_fired",
                "flag": one_shot_flag
            })
            return
        var graph_id := String(binding.get("event_graph", ""))
        if graph_id.is_empty() or not LegacyEvents.has_graph(graph_id):
            push_error("OpenAzrael v137: active trigger has no valid event graph: %s/%s" % [current_room_id, trigger_name])
            CandidateDiagnostics.record_event("trigger_event_dispatch", {
                "room": current_room_id,
                "trigger": trigger_name,
                "class": trigger_class,
                "status": "FAIL_MISSING_GRAPH",
                "graph": graph_id
            })
            return
        var applied := LegacyEvents.run(graph_id)
        CandidateDiagnostics.record_event("trigger_event_dispatch", {
            "room": current_room_id,
            "trigger": trigger_name,
            "class": trigger_class,
            "status": "DISPATCHED",
            "graph": graph_id,
            "actions": applied.size()
        })
        return

    if trigger_class in ["UNKNOWN_HOLD", "hazard_HOLD"] and entered:
        var hold_key := current_room_id + "/" + trigger_name
        if not _trigger_hold_reported.has(hold_key):
            _trigger_hold_reported[hold_key] = true
            CandidateDiagnostics.record_event("trigger_event_hold", {
                "room": current_room_id,
                "trigger": trigger_name,
                "class": trigger_class,
                "status": "HOLD_NO_GUESSED_SIDE_EFFECT"
            })

func _update_diagnostic_trigger_states() -> void:
    if evidence.is_empty() or not evidence.has("rooms") or not evidence["rooms"].has(current_room_id):
        return
    for trigger in evidence["rooms"][current_room_id].get("triggers", []):
        var trigger_name := String(trigger.get("name", ""))
        if trigger_name.is_empty():
            continue
        var inside := _inside_trigger(player.global_position, trigger)
        var had_state := _diagnostic_inside.has(trigger_name)
        var was_inside := bool(_diagnostic_inside.get(trigger_name, false))
        if not had_state or was_inside != inside:
            _diagnostic_inside[trigger_name] = inside
            CandidateDiagnostics.observe_trigger(current_room_id, trigger_name, inside)
            # Preserve the existing quiet-initial-state rule: room spawn seeds
            # overlap state but does not masquerade as a player crossing.
            if had_state:
                _dispatch_trigger_edge(trigger_name, inside)

func _process(delta: float) -> void:
    transition_cooldown = max(0.0, transition_cooldown - delta)
    if evidence.is_empty():
        return
    _update_diagnostic_trigger_states()
    if transition_cooldown > 0.0:
        return
    for tr in evidence["demo_transitions"]:
        if tr["source_room"] != current_room_id:
            continue
        var trigger_name := String(tr["trigger"])
        if current_room_id == "R1" and trigger_name == "zxcoriR5" and not DemoState.flag("R1Door1Open"):
            continue
        if current_room_id == "R1" and trigger_name == "zxcoriR2" and not DemoState.flag("R1Door2Open"):
            continue
        var trigger := _trigger_record(current_room_id, trigger_name)
        if not trigger.is_empty() and _inside_trigger(player.global_position, trigger):
            var source := current_room_id
            var dest := String(tr["destination_room"])
            var dest_view := String(tr["destination_view"])
            CandidateDiagnostics.record_transition(source, trigger_name, dest)
            load_room(dest)
            _spawn_at_portal(dest, dest_view)
            transition_cooldown = 1.0
            return

func _debug_jump(room_id: String, view_name: String) -> void:
    CandidateDiagnostics.record_event("debug_room_jump", {"room": room_id, "view": view_name})
    load_room(room_id)
    _spawn_at_portal(room_id, view_name)
    transition_cooldown = 1.0

func _unhandled_key_input(event: InputEvent) -> void:
    if not event.pressed or event.echo:
        return
    if event.keycode == KEY_1:
        _debug_jump("R1", "spaview")
    elif event.keycode == KEY_2:
        _debug_jump("R7", "view")
    elif event.keycode == KEY_3:
        _debug_jump("R8", "Object14")
