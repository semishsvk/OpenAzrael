#!/usr/bin/env python3
from __future__ import annotations
from collections import defaultdict, deque
from dataclasses import dataclass, replace
from pathlib import Path
import argparse, hashlib, json, sys
ROOT=Path(__file__).resolve().parents[1]
EXPECTED_EVENT_GRAPHS={"R7_WELL_TONGS_USE","R7_WATER_SWITCHBOARD_SOLVED","R7_NIAMH_ACTIVATE","R8_LENS_PLACE","R8_OPTICAL_START","R8_SECRET_DOOR_OPEN","R8_TAKE_SHIELD"}
REQUEST_EVENT_OPS={"request_character_animation","request_conversation"}
ALLOWED_EVENT_OPS={"set_flag","set_puzzle_node","add_inventory","remove_inventory","play_sound"}|REQUEST_EVENT_OPS
SWITCH_SOLUTION=("well_lev02","well_weel3","well_lev02")
EXPECTED_ROOM_EDGES={("R1","zxcoriR5","R7"),("R1","zxcoriR2","R8"),("R7","zxwell2R6","R1"),("R8","zxorrery","R1")}
ACTION_NAMES=("pickup_rusty_tongs","open_r1_door1","open_r1_door2","transition_R1_R7","transition_R1_R8","transition_R7_R1","transition_R8_R1","retrieve_well_key","switch_well_lev02","switch_well_weel3","retrieve_r8_lens","place_r8_lens","start_optical_sequence","finish_optical_sequence","take_shield")

def _d(items): return dict(items)
def _p(value): return tuple(sorted(value.items(),key=lambda item:item[0]))

@dataclass(frozen=True)
class DemoState:
    room:str="R1"; inventory:tuple=(); flags:tuple=(); puzzle_nodes:tuple=(); values:tuple=(); sequence_running:bool=False
    def _get(self,field,key,default=None): return _d(getattr(self,field)).get(key,default)
    def has(self,key): return bool(self._get("inventory",key,False))
    def flag(self,key): return bool(self._get("flags",key,False))
    def puzzle(self,key): return bool(self._get("puzzle_nodes",key,False))
    def value(self,key,default=None): return self._get("values",key,default)
    def _set(self,field,key,value,erase=False):
        data=_d(getattr(self,field)); data.pop(key,None) if erase else data.__setitem__(key,value)
        return replace(self,**{field:_p(data)})
    def add_inventory(self,key): return self._set("inventory",key,True)
    def remove_inventory(self,key): return self._set("inventory",key,False,True)
    def set_flag(self,key,value=True): return self._set("flags",key,bool(value))
    def set_puzzle(self,key,value=True): return self._set("puzzle_nodes",key,bool(value))
    def set_value(self,key,value): return self._set("values",key,value)
    def persistent_payload(self):
        return [1,[[k,v] for k,v in sorted(self.inventory)],[[k,v] for k,v in sorted(self.flags)],[[k,v] for k,v in sorted(self.puzzle_nodes)],[[k,v] for k,v in sorted(self.values)]]
    def persistent_hash(self):
        raw=json.dumps(self.persistent_payload(),separators=(",",":"),ensure_ascii=False)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def apply_event_graph(state,graph,graph_id):
    audio=[]
    for action in graph["graphs"][graph_id]["actions"]:
        op=action["op"]; key=action.get("key","")
        if op=="set_flag": state=state.set_flag(key,action.get("value",True))
        elif op=="set_puzzle_node": state=state.set_puzzle(key,action.get("value",True))
        elif op=="add_inventory": state=state.add_inventory(key)
        elif op=="remove_inventory": state=state.remove_inventory(key)
        elif op=="play_sound": audio.append(action["asset"])
        elif op in REQUEST_EVENT_OPS:
            # Source-required animation/conversation requests have no persistent
            # logical-state mutation in the v108 progression model. Their
            # runtime dispatch is validated independently by v137/v138.
            pass
        else: raise ValueError(f"unsupported Event IR op: {op}")
    return state,tuple(audio)

class Model:
    def __init__(self,event_graph,trigger_ir):
        self.event_graph=event_graph
        self.room_edges={(e["source_room"],e["trigger"],e["destination_room"]) for e in trigger_ir["demo_transitions"]}
    def edge(self,a,b,c): return (a,b,c) in self.room_edges
    def attempt(self,s,a):
        audio=()
        if a=="pickup_rusty_tongs":
            if s.room=="R1" and not s.has("rusty_tongs"): return s.add_inventory("rusty_tongs"),audio
        elif a=="open_r1_door1":
            if s.room=="R1" and not s.flag("R1Door1Open"): return s.set_flag("R1Door1Open"),audio
        elif a=="open_r1_door2":
            if s.room=="R1" and s.has("well_key") and not s.flag("R1Door2Open"): return s.set_flag("FR1DoorUnlocked").set_flag("R1Door2Open"),audio
        elif a=="transition_R1_R7":
            if s.room=="R1" and s.flag("R1Door1Open") and self.edge("R1","zxcoriR5","R7"): return replace(s,room="R7",sequence_running=False),audio
        elif a=="transition_R1_R8":
            if s.room=="R1" and s.flag("R1Door2Open") and self.edge("R1","zxcoriR2","R8"): return replace(s,room="R8",sequence_running=False),audio
        elif a=="transition_R7_R1":
            if s.room=="R7" and self.edge("R7","zxwell2R6","R1"): return replace(s,room="R1",sequence_running=False),audio
        elif a=="transition_R8_R1":
            if s.room=="R8" and self.edge("R8","zxorrery","R1"): return replace(s,room="R1",sequence_running=False),audio
        elif a=="retrieve_well_key":
            if s.room=="R7" and s.has("rusty_tongs") and not s.has("well_key"):
                # The production physical route from the R7 portal to WellKey
                # crosses zxactghost before the key interaction. Preserve that
                # source-backed persistent side effect in the success oracle.
                if not s.flag("R7NiamhActivated"):
                    s,_=apply_event_graph(s,self.event_graph,"R7_NIAMH_ACTIVATE")
                s,audio=apply_event_graph(s,self.event_graph,"R7_WELL_TONGS_USE")
                return s.add_inventory("well_key").remove_inventory("rusty_tongs").set_puzzle("R7KeyTake").set_flag("R7key"),audio
        elif a in ("switch_well_lev02","switch_well_weel3"):
            if s.room=="R7" and not s.flag("R8BathDrain"):
                control=a.removeprefix("switch_"); step=int(s.value("R7SwitchStep",0))
                if not 0<=step<len(SWITCH_SOLUTION): raise AssertionError(f"reachable invalid R7SwitchStep: {step}")
                if control==SWITCH_SOLUTION[step]:
                    step+=1; s=s.set_value("R7SwitchStep",step)
                    if step==len(SWITCH_SOLUTION): return apply_event_graph(s,self.event_graph,"R7_WATER_SWITCHBOARD_SOLVED")
                    return s,audio
                return s.set_value("R7SwitchStep",0),audio
        elif a=="retrieve_r8_lens":
            if s.room=="R8" and s.flag("R8BathDrain") and not s.has("r8_lens") and not s.puzzle("R8LensPlace"): return s.add_inventory("r8_lens").set_flag("R8Lens"),audio
        elif a=="place_r8_lens":
            if s.room=="R8" and s.has("r8_lens") and not s.puzzle("R8LensPlace"): return apply_event_graph(s,self.event_graph,"R8_LENS_PLACE")
        elif a=="start_optical_sequence":
            if s.room=="R8" and s.puzzle("R8LensPlace") and not s.puzzle("DoorR8") and not s.sequence_running:
                s,audio=apply_event_graph(s,self.event_graph,"R8_OPTICAL_START"); return replace(s,sequence_running=True),audio
        elif a=="finish_optical_sequence":
            if s.room=="R8" and s.sequence_running and not s.puzzle("DoorR8"):
                s,audio=apply_event_graph(s,self.event_graph,"R8_SECRET_DOOR_OPEN"); return replace(s,sequence_running=False),audio
        elif a=="take_shield":
            if s.room=="R8" and s.puzzle("DoorR8") and not s.flag("demo_complete"): return apply_event_graph(s,self.event_graph,"R8_TAKE_SHIELD")
        elif a not in ACTION_NAMES: raise KeyError(a)
        return s,audio

def validate_inputs(event_graph,trigger_ir):
    errors=[]; graphs=event_graph.get("graphs",{})
    if set(graphs)!=EXPECTED_EVENT_GRAPHS: errors.append(f"Event IR graph set drift: {sorted(graphs)}")
    for gid,g in graphs.items():
        for i,a in enumerate(g.get("actions",[])):
            op=a.get("op")
            if op not in ALLOWED_EVENT_OPS:
                errors.append(f"unsupported Event IR op: {gid}[{i}]={op}")
            elif op in REQUEST_EVENT_OPS:
                if a.get("source_required") is not True:
                    errors.append(f"request Event IR op is not source-required: {gid}[{i}]")
                if not str(a.get("character","")).strip() or not str(a.get("family","")).strip():
                    errors.append(f"incomplete request Event IR identity: {gid}[{i}]")
                if op=="request_character_animation" and not str(a.get("target_object","")).strip():
                    errors.append(f"missing request animation target: {gid}[{i}]")
    edges={(e.get("source_room"),e.get("trigger"),e.get("destination_room")) for e in trigger_ir.get("demo_transitions",[])}
    if edges!=EXPECTED_ROOM_EDGES: errors.append(f"room edge set drift: {sorted(edges)}")
    return errors

def validate_source_contract():
    paths={"demo":ROOT/"scripts/demo_state.gd","room":ROOT/"scripts/room_manager.gd","lens":ROOT/"scripts/r8_lens_interaction.gd","bible":ROOT/"scripts/r8_bible_interaction.gd","shield":ROOT/"scripts/r8_shield_interaction.gd"}
    t={k:p.read_text(encoding="utf-8") for k,p in paths.items()}
    return {
      "godot_codec_payload":"func canonical_state_payload()" in t["demo"],
      "godot_codec_hash":"func canonical_state_hash()" in t["demo"] and "HASH_SHA256" in t["demo"],
      "switch_solution_parity":'["well_lev02", "well_weel3", "well_lev02"]' in t["demo"],
      "well_key_parity":all(x in t["demo"] for x in ('"R7KeyTake"','"R7key"','"well_key"','remove("rusty_tongs")')),
      "door2_parity":all(x in t["demo"] for x in ('"FR1DoorUnlocked"','"R1Door2Open"')),
      "tongs_pickup_parity":all(x in t["room"] for x in ('"TONG6"','"rusty_tongs"')),
      "room_transition_gate_parity":all(x in t["room"] for x in ('"zxcoriR5"','"R1Door1Open"','"zxcoriR2"','"R1Door2Open"')),
      "lens_precondition_parity":all(x in t["lens"] for x in ('"R8BathDrain"','"r8_lens"','"R8Lens"')),
      "optical_event_parity":all(x in t["bible"] for x in ('"R8_LENS_PLACE"','"R8_OPTICAL_START"','"R8_SECRET_DOOR_OPEN"')),
      "shield_event_parity":all(x in t["shield"] for x in ('"DoorR8"','"R8_TAKE_SHIELD"'))
    }

def explore(model):
    initial=DemoState(); q=deque([initial]); seen={initial}; pred={}; edges=defaultdict(list); attempts=noops=0
    while q:
        s=q.popleft()
        for a in ACTION_NAMES:
            attempts+=1; n,audio=model.attempt(s,a)
            if n==s: noops+=1; continue
            edges[s].append((a,n,audio))
            if n not in seen: seen.add(n); pred[n]=(s,a,audio); q.append(n)
    success={s for s in seen if s.flag("demo_complete")}
    rev=defaultdict(set)
    for s,out in edges.items():
        for _,n,_ in out: rev[n].add(s)
    can=set(success); q=deque(success)
    while q:
        n=q.popleft()
        for s in rev[n]:
            if s not in can: can.add(s); q.append(s)
    soft=seen-can; dead={s for s in seen if not edges[s] and s not in success}
    def path(s):
        out=[]
        while s!=initial:
            p,a,audio=pred[s]; out.append((a,audio)); s=p
        return list(reversed(out))
    trace,win=min(((path(s),s) for s in success),key=lambda x:len(x[0]))
    return initial,seen,edges,success,soft,dead,attempts,noops,win,[a for a,_ in trace],[x for _,audio in trace for x in audio]

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--out",type=Path); args=ap.parse_args()
    graph=json.loads((ROOT/"data/gameplay_event_graph_v87.json").read_text(encoding="utf-8"))
    triggers=json.loads((ROOT/"data/xaf_trigger_evidence.json").read_text(encoding="utf-8"))
    errors=validate_inputs(graph,triggers); source=validate_source_contract(); errors += [k for k,v in source.items() if not v]
    if errors: result={"schema":"openazrael.kg001.state_space","version":108,"status":"FAIL","errors":errors}
    else:
        initial,states,edges,success,soft,dead,attempts,noops,win,path,audio=explore(Model(graph,triggers))
        checks={"all_reachable_states_can_reach_success":not soft,"no_non_success_dead_ends":not dead,"success_reachable":bool(success),"shortest_path_ends_in_demo_complete":win.flag("demo_complete"),"canonical_hash_is_order_invariant":DemoState(inventory=(("b",True),("a",True))).persistent_hash()==DemoState(inventory=(("a",True),("b",True))).persistent_hash()}
        failed=[k for k,v in checks.items() if not v]
        result={"schema":"openazrael.kg001.state_space","version":108,"scope":"source-safe logical model for KG-001 G02/G03 preparation; Godot runtime execution remains separate","status":"PASS" if not failed else "FAIL","reachable_states":len(states),"changed_transition_edges":sum(len(x) for x in edges.values()),"action_attempts":attempts,"invalid_or_idempotent_noops":noops,"success_states":len(success),"softlock_states":len(soft),"non_success_dead_end_states":len(dead),"shortest_success_action_count":len(path),"shortest_success_path":path,"shortest_success_audio_events":audio,"initial_persistent_state_sha256":initial.persistent_hash(),"shortest_success_persistent_state_sha256":win.persistent_hash(),"source_contract_checks":source,"exploration_checks":checks,"forensic_boundary":{"does_not_prove_original_timing_or_motion":True,"does_not_promote_event_actions_above_existing_confidence":True,"godot_runtime_execution_required_for_final_kg001":True}}
        if failed: result["errors"]=failed
    if args.out: args.out.parent.mkdir(parents=True,exist_ok=True); args.out.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2)); sys.exit(0 if result["status"]=="PASS" else 1)
if __name__=="__main__": main()
