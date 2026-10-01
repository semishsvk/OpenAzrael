from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
def read(p):return (ROOT/p).read_text(encoding="utf-8")

def test_generic_book_adapter_contains_complete_available_demo_family():
    s=read("scripts/book_presentation_v172.gd")
    for x in ["R1/r1p1","R1/r3t1","R8/r8t3","R8/r8t4"]:
        assert x in s
    assert "R7/r7p1" not in s

def test_tapestry_pickup_applies_state_before_book_presentation():
    s=read("scripts/book_pickup_interaction_v172.gd")
    assert s.index("DemoState.acquire(item_id)") < s.index("BookPresentation.open")
    assert 'return "TAKE"' in s

def test_room_manager_binds_only_verified_tapestry_book_pickups():
    s=read("scripts/room_manager.gd")
    assert 'object_name in ["r3t1", "r8t3", "r8t4"]' in s
    assert 'book_pickup_interaction_v172.gd' in s
    block=s[s.index("const PICKUPS :="):s.index("var current_room_id")]
    assert '"r1p1"' not in block

def test_rmb_close_is_pre_gui_input_and_modal():
    s=read("scripts/interaction_presentation_host_v158.gd")
    assert "func _input(event: InputEvent)" in s
    assert "MOUSE_BUTTON_RIGHT" in s
    assert "set_input_as_handled()" in s
