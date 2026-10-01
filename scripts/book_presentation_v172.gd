extends RefCounted
## Shared source-backed adapter for the original opcode-0x21 book-view action.
const SOURCE_TEXTURES := {
    "R1/r1p1": "res://assets/source_books/1_1_0.png",
    "R1/r3t1": "res://assets/source_books/r3t1_0.png",
    "R8/r8t3": "res://assets/source_books/r8t3_0.png",
    "R8/r8t4": "res://assets/source_books/r8t4_0.png",
}

static func open(scene: Node, presentation_id: String) -> bool:
    if scene == null or not SOURCE_TEXTURES.has(presentation_id):
        return false
    var host := scene.get_node_or_null("InteractionPresentationV158")
    if host == null or not host.has_method("open_source_texture"):
        push_warning("OpenAzrael v172: book-view host unavailable for " + presentation_id)
        return false
    var source_path := String(SOURCE_TEXTURES[presentation_id])
    if not ResourceLoader.exists(source_path):
        push_warning("OpenAzrael v172: verified source book page not staged: " + source_path)
        return false
    var texture := load(source_path) as Texture2D
    if texture == null:
        push_warning("OpenAzrael v172: failed to load source book page: " + source_path)
        return false
    return bool(host.call("open_source_texture", presentation_id, texture))
