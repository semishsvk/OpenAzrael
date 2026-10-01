from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[3]

def read(p): return (ROOT/p).read_text(encoding="utf-8")

def test_r1p1_is_not_generic_pickup():
    room=read("scripts/room_manager.gd")
    pickup_block=room[room.index("const PICKUPS :="):room.index("var current_room_id")]
    assert '"r1p1"' not in pickup_block
    assert '_setup_readable_objects(id)' in room
    assert 'Interact_r1p1' in room

def test_r1p1_runtime_is_look_book_view():
    src=read("scripts/readable_book_interaction_v162.gd")
    assert 'return "LOOK"' in src
    assert 'DemoState.acquire(ITEM_ID)' in src\n    assert src.index('visual_node.visible = false') < src.index('DemoState.acquire(ITEM_ID)') < src.index('BookPresentation.open')
    assert 'BookPresentation.open(get_tree().current_scene, PRESENTATION_ID)' in src
    adapter=read("scripts/book_presentation_v172.gd")
    assert '"R1/r1p1": "res://assets/source_books/1_1_0.png"' in adapter

def test_book_view_has_source_verified_rmb_exit_and_modal_guards():
    host=read("scripts/interaction_presentation_host_v158.gd")
    assert "MOUSE_BUTTON_RIGHT" in host and "close()" in host
    assert "_presentation_open()" in read("scripts/player.gd")
    assert "_presentation_open()" in read("scripts/interaction_probe.gd")

def test_pppv_observes_presentation_lifecycle():
    runner=read("scripts/validation/pppv_scenario_runner.gd")
    assert 'attach_presentation(scene.get_node_or_null("InteractionPresentationV158"))' in runner

def test_parchment_contract_preserves_verified_remove_carry_book_lifecycle():
    c=json.loads(read("data/tests/kg001_parchment_r1_pppv_contract_v158.json"))
    assert c["scenario_id"]=="openazrael.r1.look_at_parchment"
    seq=c["required_sequence"]
    assert any(x.get("kind")=="state_transition" and x.get("before") is False and x.get("after") is True and x.get("source_opcode")=="0x08" for x in seq)
    assert any(x.get("kind")=="world_object" and x.get("visible_after") is False and x.get("source_opcode")=="0x07" for x in seq)
    assert any(x.get("kind")=="presentation" and x.get("state")=="OPEN" and x.get("source_opcode")=="0x21" for x in seq)
