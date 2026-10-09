from pathlib import Path
p=Path(r"F:\Remaster Framework\work\OpenAzrael")/"scripts/room_manager.gd";s=p.read_text(encoding="utf-8")
s=s.replace('''    if current_room_id == "R7":
        _add_scan_only_area("wel_well", "R7Well", 28.0)
    elif current_room_id == "R8":''','''    if current_room_id == "R1":
        _add_scan_only_area("textwall", "R1WallText", 18.0)
    elif current_room_id == "R7":
        _add_scan_only_area("wel_well", "R7Well", 28.0)
    elif current_room_id == "R8":''',1)
s=s.replace('''            ["mirror", "R8WindowMirror", 18.0],
        ]''','''            ["mirror", "R8WindowMirror", 18.0],
            ["lenstop01", "R8LensLook", 14.0],
            ["broken3", "R8MirrorHole", 16.0],
            ["ZZcutter02", "R8Water1", 20.0],
        ]''',1)
p.write_text(s,encoding="utf-8")
print("FOUR_SOURCE_NODES_BOUND")
