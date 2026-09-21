#!/usr/bin/env python3
from pathlib import Path
import json, math, sys

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_ROOMS = {"R1", "R7", "R8"}
EXPECTED_TRANSITIONS = {
    ("R1", "zxcoriR5", "R7", "spaview", "view"),
    ("R1", "zxcoriR2", "R8", "entcori", "Object14"),
    ("R7", "zxwell2R6", "R1", "view", "spaview"),
    ("R8", "zxorrery", "R1", "Object14", "entcori"),
}
EXPECTED_GRAPHS = {
    "R7_WATER_SWITCHBOARD_SOLVED", "R7_WELL_TONGS_USE",
    "R8_LENS_PLACE", "R8_OPTICAL_START",
    "R8_SECRET_DOOR_OPEN", "R8_TAKE_SHIELD",
}
ALLOWED_OPS = {"set_flag", "set_puzzle_node", "add_inventory", "remove_inventory", "play_sound"}
errors = []
def fail(message): errors.append(message)
def finite_vec3(value):
    return isinstance(value, list) and len(value)==3 and all(isinstance(x,(int,float)) and math.isfinite(x) for x in value)

try: events=json.loads((ROOT/"data/gameplay_event_graph_v87.json").read_text(encoding="utf-8"))
except Exception as exc: fail(f"event graph parse: {exc}"); events={}
try: xaf=json.loads((ROOT/"data/xaf_trigger_evidence.json").read_text(encoding="utf-8"))
except Exception as exc: fail(f"trigger IR parse: {exc}"); xaf={}

if events:
    graphs=events.get("graphs",{})
    if set(graphs)!=EXPECTED_GRAPHS: fail(f"event graph ids drift: {sorted(graphs)}")
    for graph_id,graph in graphs.items():
        actions=graph.get("actions",[])
        if not actions: fail(f"empty event graph: {graph_id}")
        for index,action in enumerate(actions):
            op=action.get("op")
            if op not in ALLOWED_OPS: fail(f"unsupported op {graph_id}[{index}]: {op}")
            if not action.get("confidence"): fail(f"missing confidence {graph_id}[{index}]")
            if op!="play_sound" and not action.get("key"): fail(f"missing state key {graph_id}[{index}]")
            if op=="play_sound":
                asset=str(action.get("asset",""))
                if not asset.upper().endswith(".WAV") or "/" in asset or "\\" in asset:
                    fail(f"unsafe/invalid sound asset {graph_id}[{index}]: {asset}")
    if not events.get("hold"): fail("event graph HOLD boundary missing")

if xaf:
    if xaf.get("schema")!=1: fail("trigger IR schema drift")
    rooms=xaf.get("rooms",{})
    if set(rooms)!=EXPECTED_ROOMS: fail(f"room set drift: {sorted(rooms)}")
    trigger_names={}; portal_names={}
    for room_id,room in rooms.items():
        trigger_names[room_id]={item.get("name") for item in room.get("triggers",[])}
        portal_names[room_id]={item.get("name") for item in room.get("portal_views",[])}
        for item in room.get("triggers",[]):
            bounds=item.get("bounds")
            if not finite_vec3(item.get("centroid")) or not isinstance(bounds,list) or len(bounds)!=2 or not all(finite_vec3(v) for v in bounds):
                fail(f"invalid trigger geometry metadata: {room_id}/{item.get('name')}")
        for item in room.get("portal_views",[]):
            bounds=item.get("bounds"); normal=item.get("normal")
            if not finite_vec3(item.get("centroid")) or not finite_vec3(normal) or not isinstance(bounds,list) or len(bounds)!=2 or not all(finite_vec3(v) for v in bounds):
                fail(f"invalid portal metadata: {room_id}/{item.get('name')}")
            elif not 0.98 <= math.sqrt(sum(float(x)*float(x) for x in normal)) <= 1.02:
                fail(f"portal normal not unit length: {room_id}/{item.get('name')}")
    actual=set()
    for tr in xaf.get("demo_transitions",[]):
        edge=(tr.get("source_room"),tr.get("trigger"),tr.get("destination_room"),tr.get("source_view"),tr.get("destination_view"))
        actual.add(edge)
        sr,trigger,dr,source_view,destination_view=edge
        if sr not in rooms or dr not in rooms: fail(f"transition references unknown room: {edge}"); continue
        if trigger not in trigger_names[sr]: fail(f"transition trigger missing: {edge}")
        if source_view not in portal_names[sr]: fail(f"source portal missing: {edge}")
        if destination_view not in portal_names[dr]: fail(f"destination portal missing: {edge}")
        if tr.get("confidence")!="high": fail(f"transition confidence drift: {edge}")
    if actual!=EXPECTED_TRANSITIONS: fail(f"transition set drift: {sorted(actual)}")

if errors:
    print("OpenAzrael demo runtime IR validation: FAIL")
    [print(" -",x) for x in errors]
    sys.exit(1)
print("OpenAzrael demo runtime IR validation: PASS")
print(" event graphs:",len(events["graphs"]))
print(" rooms:",len(xaf["rooms"]))
print(" transitions:",len(xaf["demo_transitions"]))
