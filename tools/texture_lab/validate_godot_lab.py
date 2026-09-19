#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCENE = ROOT / "tools/texture_lab/godot/texture_lab.tscn"
SCRIPT = ROOT / "tools/texture_lab/godot/texture_lab.gd"
SELECTION = ROOT / "tools/texture_lab/config/rt_poc_01_selection.json"
PROFILE_RESOLVER = ROOT / "tools/texture_lab/godot/texture_profile_resolver.gd"
RUNTIME_RESOURCE_LOADER = ROOT / "tools/texture_lab/godot/runtime_texture_resource_loader.gd"


def main() -> int:
    assert SCENE.is_file(), SCENE
    assert SCRIPT.is_file(), SCRIPT
    assert SELECTION.is_file(), SELECTION
    assert PROFILE_RESOLVER.is_file(), PROFILE_RESOLVER
    assert RUNTIME_RESOURCE_LOADER.is_file(), RUNTIME_RESOURCE_LOADER
    scene = SCENE.read_text(encoding="utf-8")
    script = SCRIPT.read_text(encoding="utf-8")
    resolver = PROFILE_RESOLVER.read_text(encoding="utf-8")
    runtime_loader = RUNTIME_RESOURCE_LOADER.read_text(encoding="utf-8")

    assert 'path="res://tools/texture_lab/godot/texture_lab.gd"' in scene
    for token in [
        "assets/textures/classic",
        "assets/textures/enhanced",
        "assets/textures/ai_restored",
        "assets/textures/ai_recreated",
        "Image.load_from_file",
        "KEY_1",
        "KEY_2",
        "KEY_3",
        "KEY_4",
        "KEY_T",
        "KEY_L",
        "KEY_B",
        "KEY_R",
        "KEY_P",
        "KEY_S",
        "PROFILE_MANIFEST_PATH",
        "texture_profile_resolver.gd",
        "SurfaceB",
        "compare_mode",
        "reference_tier_index",
    ]:
        assert token in script, token

    for forbidden in [
        "DemoState.",
        "CandidateDiagnostics.",
        "RoomManager",
        "load_room(",
        "set_flag(",
        "set_puzzle",
    ]:
        assert forbidden not in script, forbidden


    for token in [
        'EXPECTED_SCHEMA := "openazrael.texture_lab.runtime_texture_manifest.v1"',
        'ALLOWED_PREFIX := "res://assets/textures/"',
        'automatic_promotion',
        'path.contains("..")',
        'path.ends_with(".png")',
        "HashingContext.new()",
        "HashingContext.HASH_SHA256",
        "runtime_ready",
        "sha256",
        "size_bytes",
    ]:
        assert token in resolver, token

    for forbidden in [
        "DemoState.",
        "CandidateDiagnostics.",
        "RoomManager",
        "load_room(",
        "set_flag(",
        "set_puzzle",
        "production_selection.json",
    ]:
        assert forbidden not in resolver, forbidden


    for token in [
        'ALLOWED_PREFIX := "res://assets/textures/"',
        "ResourceLoader.load(path)",
        "resource is Texture2D",
        'path.ends_with(".png")',
    ]:
        assert token in runtime_loader, token

    for forbidden in [
        "FileAccess",
        "HashingContext",
        "production_selection.json",
        "DemoState.",
        "RoomManager",
    ]:
        assert forbidden not in runtime_loader, forbidden

    print("PASS Texture Lab Godot source contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
