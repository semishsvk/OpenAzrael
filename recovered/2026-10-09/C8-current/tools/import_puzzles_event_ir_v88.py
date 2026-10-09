#!/usr/bin/env python3
from pathlib import Path
import argparse,json,re,hashlib

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
    out=[]
    for i in range(len(data)-4):
        if data[i:i+2]!=b'\x10\x00':continue
        op=data[i+2]; tok=printable_token(data,i+3)
        if tok is None:continue
        name,conf=SEM.get(op,("unknown_legacy_opcode","UNKNOWN"))
        rec={"source_offset":i,"source_offset_hex":f"0x{i:x}","legacy_opcode":op,
             "legacy_opcode_hex":f"0x{op:02x}","token":tok,"ir_op":name,"confidence":conf,
             "provenance":"PUZZLES.DAT byte-pattern 10 00 <opcode> <printable NUL token>"}
        if op==0x28:
            rec["asset_candidate"]=tok+("" if tok.lower().endswith('.wav') else ".WAV")
        out.append(rec)
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--puzzles',required=True); ap.add_argument('--out',required=True)
    a=ap.parse_args(); p=Path(a.puzzles); data=p.read_bytes(); recs=scan(data)
    counts={}
    for r in recs: counts[r['legacy_opcode_hex']]=counts.get(r['legacy_opcode_hex'],0)+1
    obj={"version":88,"format":"OpenAzrael conservative PUZZLES.DAT event IR corpus",
         "source":{"name":p.name,"size":len(data),"sha256":hashlib.sha256(data).hexdigest()},
         "grammar_status":"PARTIAL_PATTERN_CORPUS_NOT_FULL_GRAMMAR",
         "execution_policy":"NOT_DIRECTLY_EXECUTABLE: records are candidates until enclosing record grammar and operands are proven.",
         "record_count":len(recs),"opcode_counts":dict(sorted(counts.items())),"records":recs,
         "hold":["Record boundaries/enclosing PUZZLR grammar not yet decoded.","Exact operands beyond opcode+token are not imported.","UNKNOWN opcodes never acquire guessed semantics.","HIGH semantics identify operation family, not necessarily set/clear direction or timing."]}
    Path(a.out).write_text(json.dumps(obj,indent=2)+"\n",encoding='utf-8')
    print(json.dumps({"records":len(recs),"opcodes":len(counts),"sha256":obj['source']['sha256']},sort_keys=True))
if __name__=='__main__':main()
