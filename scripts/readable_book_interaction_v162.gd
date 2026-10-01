extends Area3D
## Source-backed R1 parchment interaction.
## The original demo README classifies this object as a parchment "to look at".
## It is not an inventory pickup.

const PRESENTATION_ID := "R1/r1p1"
const SOURCE_TEXTURE := "res://assets/source_books/1_1_0.png"

func interact() -> void:
    var scene := get_tree().current_scene
    if scene == null:
        return
    var host := scene.get_node_or_null("InteractionPresentationV158")
    if host == null or not host.has_method("open_source_texture"):
        push_warning("OpenAzrael v162: book-view host unavailable for R1/r1p1")
        return
    if not ResourceLoader.exists(SOURCE_TEXTURE):
        push_warning("OpenAzrael v162: verified R1/r1p1 source page not staged: " + SOURCE_TEXTURE)
        return
    var texture := load(SOURCE_TEXTURE) as Texture2D
    if texture == null:
        push_warning("OpenAzrael v162: failed to load verified R1/r1p1 source page")
        return
    host.call("open_source_texture", PRESENTATION_ID, texture)

func interaction_cursor_id() -> String:
    return "LOOK"
