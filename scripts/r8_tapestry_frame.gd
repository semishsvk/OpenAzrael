extends Area3D

var required_item := ""
var state_flag := ""
var piece_visual: Node3D
var frame_visual: Node3D

const TAP_SOUND = preload("res://assets/audio/797TAP.WAV")

func _play_one_shot(stream: AudioStream) -> void:
    var p := AudioStreamPlayer.new()
    p.stream = stream
    get_tree().current_scene.add_child(p)
    p.finished.connect(p.queue_free)
    p.play()

func _align_piece_to_frame() -> void:
    if not is_instance_valid(piece_visual) or not is_instance_valid(frame_visual):
        return
    # XAF evidence shows the completed tapestry meshes are staged ~493.7 X units
    # away from the corresponding frames with essentially the same orientation.
    # Preserve the piece basis and translate its visual bounds onto the frame bounds.
    var piece_mesh := _first_mesh(piece_visual)
    var frame_mesh := _first_mesh(frame_visual)
    if piece_mesh == null or frame_mesh == null:
        piece_visual.global_position = frame_visual.global_position
        return
    var pc := _mesh_world_center(piece_mesh)
    var fc := _mesh_world_center(frame_mesh)
    piece_visual.global_position += fc - pc

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
    _play_one_shot(TAP_SOUND)
    if DemoState.flag("R8Tap1") and DemoState.flag("R8Tap3") and DemoState.flag("R8Tap4"):
        DemoState.set_flag("R8TapestryComplete")
        print("All three loose tapestry pieces are back in their frames.")
    else:
        print("Placed tapestry piece in its frame.")
