#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCENE = ROOT / "tools/texture_lab/godot/texture_lab.tscn"
SCRIPT = ROOT / "tools/texture_lab/godot/texture_lab.gd"
SELECTION = ROOT / "tools/texture_lab/config/rt_poc_01_selection.json"


def main() -> int:
    assert SCENE.is_file(), SCENE
    assert SCRIPT.is_file(), SCRIPT
    assert SELECTION.is_file(), SELECTION
    scene = SCENE.read_text(encoding="utf-8")
    script = SCRIPT.read_text(encoding="utf-8")

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
        "KEY_S",
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

    print("PASS Texture Lab Godot source contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
