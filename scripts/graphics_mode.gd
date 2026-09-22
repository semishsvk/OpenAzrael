extends Node

# OpenAzrael presentation layer. Gameplay/world coordinates remain shared.
enum GraphicsMode { CLASSIC, ENHANCED, REMASTERED }

var mode: int = GraphicsMode.CLASSIC

func mode_name() -> String:
    match mode:
        GraphicsMode.CLASSIC: return "CLASSIC"
        GraphicsMode.ENHANCED: return "ENHANCED"
        GraphicsMode.REMASTERED: return "REMASTERED"
    return "CLASSIC"

func set_mode(next_mode: int) -> void:
    mode = next_mode
    # v44 ships the validated Classic asset path. Enhanced and Remastered are
    # architecture slots only; never silently substitute generated assets.
    if mode != GraphicsMode.CLASSIC:
        push_warning("OpenAzrael v44: %s graphics assets are not built yet; Classic remains the validated presentation." % mode_name())

func classic_asset_status() -> Dictionary:
    return {
        "rooms": ["R1", "R7", "R8"],
        "decoded_azf_textures": 86,
        "coordinate_space": "AZRAEL_WORLD_XYZ",
        "texture_decode": "VERIFIED_DEMO_CORPUS",
        "godot_visual_parity": "HOLD"
    }
