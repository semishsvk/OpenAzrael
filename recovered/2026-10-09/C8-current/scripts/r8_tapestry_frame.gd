extends Area3D

var required_item := ""
var state_flag := ""
var piece_visual: Node3D
var frame_visual: Node3D

func _align_piece_to_frame() -> void:
    if not is_instance_valid(piece_visual) or not is_instance_valid(frame_visual):
        return
    # XAF evidence shows the completed tapestry meshes are staged ~493.7 X units
    # away from the corresponding frames with essentially the same orientation.
    # Installed pieces use the frame orientation. The staged tapestry4 has a
    # one-degree pitch which clips its upper half behind the frame backing.
    # Keep authored vertices/UVs; correct only the placement transform.
    var piece_mesh := _first_mesh(piece_visual)
    var frame_mesh := _first_mesh(frame_visual)
    if piece_mesh == null or frame_mesh == null:
        piece_visual.global_position = frame_visual.global_position
        return
    piece_visual.global_basis = frame_visual.global_basis
    var pc := _mesh_world_center(piece_mesh)
    var fc := _mesh_world_center(frame_mesh)
    # Separate coincident front faces; repeated sync remains idempotent.
    var outward := frame_visual.global_basis.z.normalized()
    piece_visual.global_position += fc - pc + outward * 0.05

func _first_mesh(root: Node) -> MeshInstance3D:
    if root is MeshInstance3D:
        return root as MeshInstance3D
    for c in root.get_children():
        var m := _first_mesh(c)
        if m != null:
            return m
    return null

func _mesh_world_center(mi: MeshInstance3D) -> Vector3:
    var a := mi.get_aabb()
    return mi.to_global(a.get_center())

func sync_from_state() -> void:
    if not is_instance_valid(piece_visual):
        return
    if DemoState.flag(state_flag):
        _align_piece_to_frame()
        piece_visual.visible = true
    else:
        piece_visual.visible = false

func interact() -> void:
    if DemoState.flag(state_flag):
        return
    if not DemoState.has(required_item):
        print("An empty tapestry frame. The matching piece is missing.")
        return
    DemoState.remove(required_item)
    DemoState.set_flag(state_flag)
    _align_piece_to_frame()
    if is_instance_valid(piece_visual):
        piece_visual.visible = true
    LegacyEvents.run("R8_TAPESTRY_FRAME_TAP_SOUND")
    if DemoState.flag("R8Tap1") and DemoState.flag("R8Tap3") and DemoState.flag("R8Tap4"):
        DemoState.set_flag("R8TapestryComplete")
        print("All three loose tapestry pieces are back in their frames.")
    else:
        print("Placed tapestry piece in its frame.")

func interaction_cursor_id() -> String:
    if DemoState.flag(state_flag):
        return "CANT"
    return "USE" if DemoState.has(required_item) else "CANT"
