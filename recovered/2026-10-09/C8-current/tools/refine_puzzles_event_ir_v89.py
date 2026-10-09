#!/usr/bin/env python3
from pathlib import Path
import argparse,json,re,hashlib,collections

def printable_token(data,start,maxlen=96):
    end=data.find(b'\0',start,min(len(data),start+maxlen))
    if end<0 or end==start:return None
    raw=data[start:end]
    if len(raw)>64 or any(c<32 or c>=127 for c in raw):return None
    s=raw.decode('ascii','replace')
    return s if re.search(r'[A-Za-z]',s) else None

SEM={
0x00:("timer_start","HIGH"),0x01:("timer_stop_or_remove","MEDIUM-HIGH"),
0x04:("persistent_flag_operation","HIGH"),0x07:("add_object_to_room","HIGH"),
0x08:("remove_object_from_room","HIGH"),0x09:("remove_inventory_item","HIGH"),
0x17:("object_control_operation","MEDIUM"),0x18:("move_or_animate_object","MEDIUM-HIGH"),
0x19:("object_position_or_state_transition","MEDIUM-HIGH"),0x22:("play_movie","HIGH"),
0x28:("play_sound","HIGH")}

def scan(data):
    candidates=[]; rejected=[]
    for i in range(len(data)-4):
        if data[i:i+2]!=b'\x10\x00': continue
        op=data[i+2]; tok=printable_token(data,i+3)
        if tok is None: continue
        base={"source_offset":i,"source_offset_hex":f"0x{i:x}","legacy_opcode":op,
              "legacy_opcode_hex":f"0x{op:02x}","token":tok}
        # v88 collision: 10 00 + ASCII "Event\0" was parsed as opcode 0x45 ('E') + token "vent".
        if data[i+2:i+8] == b'Event\0':
            base.update({"rejection_reason":"LEXICAL_EVENT_MARKER_COLLISION",
                         "evidence":"bytes are exactly 10 00 45 76 65 6e 74 00 = 10 00 + ASCII Event\\0; 0x45 is not established as an opcode here"})
            rejected.append(base); continue
        name,conf=SEM.get(op,("unknown_legacy_opcode","UNKNOWN"))
        base.update({"ir_op":name,"confidence":conf,
                     "provenance":"PUZZLES.DAT byte-pattern 10 00 <opcode> <printable NUL token>, excluding proven lexical Event collision"})
        if op==0x28: base["asset_candidate"]=tok+("" if tok.lower().endswith('.wav') else ".WAV")
        candidates.append(base)
    return candidates,rejected

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--puzzles',required=True); ap.add_argument('--out',required=True); a=ap.parse_args()
    p=Path(a.puzzles); data=p.read_bytes(); recs,rej=scan(data)
    counts=collections.Counter(r['legacy_opcode_hex'] for r in recs)
    obj={"version":89,"format":"OpenAzrael refined conservative PUZZLES.DAT Event IR corpus",
         "source":{"name":p.name,"size":len(data),"sha256":hashlib.sha256(data).hexdigest()},
         "supersedes":"v88 candidate count included a deterministic lexical collision: 10 00 Event\\0 was misread as opcode 0x45 + token vent.",
         "grammar_status":"PARTIAL_PATTERN_CORPUS_NOT_FULL_GRAMMAR",
         "execution_policy":"NOT_DIRECTLY_EXECUTABLE",
         "candidate_count":len(recs),"rejected_lexical_collision_count":len(rej),
         "opcode_counts":dict(sorted(counts.items())),"records":recs,"rejected_records":rej,
         "hold":["Record boundaries/enclosing PUZZLR grammar not yet decoded.","Exact operands beyond opcode+token are not imported.","UNKNOWN opcodes never acquire guessed semantics.","Other lexical collisions may remain until the enclosing grammar is proven."]}
    Path(a.out).write_text(json.dumps(obj,indent=2)+"\n",encoding='utf-8')
    print(json.dumps({"candidates":len(recs),"rejected":len(rej),"opcodes":len(counts),"sha256":obj['source']['sha256']},sort_keys=True))
if __name__=='__main__': main()
