#!/usr/bin/env python3
from pathlib import Path
import json,re,sys
ROOT=Path(__file__).resolve().parents[1]
contract=json.loads((ROOT/"data/tests/kg001_demo_connectivity_contract_v140.json").read_text(encoding="utf-8"))
evidence=json.loads((ROOT/"data/xaf_trigger_evidence.json").read_text(encoding="utf-8"))
manager=(ROOT/"scripts/room_manager.gd").read_text(encoding="utf-8")

expected={(r["source"],r["trigger"],r["destination"],r["source_view"],r["destination_view"]) for r in contract["directed_transitions"]}
actual={(str(r["source_room"]),str(r["trigger"]),str(r["destination_room"]),str(r["source_view"]),str(r["destination_view"])) for r in evidence.get("demo_transitions",[])}

rooms=set(contract["rooms"])
room_evidence=evidence.get("rooms",{})
def trigger_names(room):
    return {str(x.get("name","")) for x in room_evidence.get(room,{}).get("triggers",[])}
def view_names(room):
    return {str(x.get("name","")) for x in room_evidence.get(room,{}).get("portal_views",[])}

# Directed reachability / strong connectivity.
adj={room:set() for room in rooms}
for src,trig,dst,sv,dv in actual:
    if src in adj: adj[src].add(dst)
def reachable(start):
    seen={start}; stack=[start]
    while stack:
        cur=stack.pop()
        for nxt in adj.get(cur,set()):
            if nxt not in seen:
                seen.add(nxt); stack.append(nxt)
    return seen

record_checks=[]
for src,trig,dst,sv,dv in expected:
    record_checks.append(
        src in room_evidence and dst in room_evidence
        and trig in trigger_names(src)
        and sv in view_names(src)
        and dv in view_names(dst)
    )

checks={
 "schema":contract.get("schema")=="openazrael.kg001.demo_connectivity_closure_contract" and contract.get("version")==140,
 "exact_rooms":rooms=={"R1","R7","R8"} and set(room_evidence).issuperset(rooms),
 "exact_edges":actual==expected and len(actual)==4,
 "source_records":all(record_checks),
 "strongly_connected":all(reachable(room)==rooms for room in rooms),
 "reciprocal_R1_R7":("R1","R7") in {(a,c) for a,b,c,d,e in actual} and ("R7","R1") in {(a,c) for a,b,c,d,e in actual},
 "reciprocal_R1_R8":("R1","R8") in {(a,c) for a,b,c,d,e in actual} and ("R8","R1") in {(a,c) for a,b,c,d,e in actual},
 "room_manager_paths":all(token in manager for token in ('"R1": "res://assets/rooms/R1.glb"','"R7": "res://assets/rooms/R7.glb"','"R8": "res://assets/rooms/R8.glb"')),
 "manager_uses_transition_evidence":'for tr in evidence["demo_transitions"]' in manager,
 "door1_gate":'trigger_name == "zxcoriR5"' in manager and 'R1Door1Open' in manager,
 "door2_gate":'trigger_name == "zxcoriR2"' in manager and 'R1Door2Open' in manager,
}
failed=[k for k,v in checks.items() if not v]
print(json.dumps({
 "schema":"openazrael.kg001.demo_connectivity_contract_validation",
 "version":140,
 "status":"SOURCE_CONTRACT_PASS" if not failed else "FAIL",
 "runtime_status":"NOT_EXECUTED",
 "checks":checks,
 "failed":failed,
 "adjacency":{k:sorted(v) for k,v in adj.items()},
},indent=2))
sys.exit(1 if failed else 0)
