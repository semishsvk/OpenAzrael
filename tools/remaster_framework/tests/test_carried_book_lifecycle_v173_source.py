from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[3]
def read(p):return (ROOT/p).read_text(encoding="utf-8")

def test_opcode_lifecycle_is_bound_to_runtime_order():
    e=json.loads(read("data/tests/kg001_object_carry_book_opcode_evidence_v173.json"))
    assert e["opcode_handlers"]["0x07"]["semantics"]=="REMOVE_OR_DEACTIVATE_WORLD_OBJECT"
    assert e["opcode_handlers"]["0x08"]["semantics"]=="ADD_OBJECT_TO_CARRIED_SET_AND_UI"
    assert e["opcode_handlers"]["0x09"]["semantics"]=="REMOVE_OBJECT_FROM_CARRIED_SET_AND_UI"
    assert e["opcode_handlers"]["0x21"]["semantics"]=="OPEN_BOOK_VIEW_FOR_WORLD_OBJECT"

def test_r1_executes_remove_then_carry_then_book():
    s=read("scripts/readable_book_interaction_v162.gd")
    assert s.index("visual_node.visible = false") < s.index("DemoState.acquire(ITEM_ID)") < s.index("BookPresentation.open")

def test_r3_and_r8_preserve_source_action_order_class():
    room=read("scripts/room_manager.gd")
    assert 'area.set("remove_before_acquire", object_name == "r3t1")' in room
    adapter=read("scripts/book_pickup_interaction_v172.gd")
    assert "remove_before_acquire" in adapter

def test_carried_hud_has_source_labels_and_no_fixed_order():
    s=read("scripts/legacy_menu_runtime_v145.gd")
    assert 'INVENTORY_ITEM_ORDER' not in s
    assert '"parchment_r1": "Page - Apr 1194"' in s
    for item in ["tapestry_piece_1","tapestry_piece_3","tapestry_piece_4"]:
        assert f'"{item}": "Tapestry Piece"' in s
    assert "for raw_id in DemoState.inventory.keys()" in s

def test_r7_is_explicit_source_incomplete_not_fabricated():
    s=read("scripts/book_presentation_v172.gd")
    assert "R7/r7p1" not in s
    e=json.loads(read("data/tests/kg001_r7p1_interaction_evidence_v166.json"))
    assert e["status"]=="BOOK_ACTION_VERIFIED_SOURCE_PAYLOAD_INCOMPLETE"
