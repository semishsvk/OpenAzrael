#!/usr/bin/env python3
from pathlib import Path
import hashlib, json, sys

src=Path(sys.argv[1]); out=Path(sys.argv[2])
raw=src.read_bytes(); lines=raw.decode("latin1").replace("\r\n","\n").splitlines()
EXPECTED_SHA="e3f0b14b64682f0e621f7f52fb998ccf8ddba4febd0ac0df4aa201f371939f71"
if hashlib.sha256(raw).hexdigest()!=EXPECTED_SHA or len(raw)!=342:
    raise SystemExit("ATDEMO_NIAMH_IDENTITY_MISMATCH")
if lines[:6] != ["1","1A","1","2","3","0"]:
    raise SystemExit("ATDEMO_NIAMH_HEADER_MISMATCH")
i=6; rows=[]
for _ in range(3):
    rid=lines[i].strip(); i+=1
    pre_n=int(lines[i]); i+=1
    pre=[lines[i+j].strip() for j in range(pre_n)]; i+=pre_n
    act_n=int(lines[i]); i+=1
    actions=[lines[i+j].strip() for j in range(act_n)]; i+=act_n
    player=lines[i]; i+=1
    response_control=[int(lines[i+j]) for j in range(3)]; i+=3
    answer=lines[i]; i+=1
    marker=lines[i].strip(); i+=1
    tail=[int(lines[i+j]) for j in range(3)]; i+=3
    if marker != f"Ni1A_{rid}": raise SystemExit("ATDEMO_NIAMH_MARKER_MISMATCH")
    rows.append({"id":rid,"source_marker":marker,"prerequisites":pre,"actions":actions,
                 "player_text":player,"response_control":response_control,
                 "niamh_text":answer,"tail_control":tail})
doc={"schema":"openazrael.demo.conversation_ir","version":253,"status":"ATDEMO_SOURCE_PARSED",
     "scope":"ATDEMO","source":{"file":"NIAMH.DAT","bytes":len(raw),"sha256":EXPECTED_SHA},
     "character":"Niamh","families":{"1A":{"declared_records":3,"records":rows}},
     "policy":{"retail_1b_not_required":True,"do_not_display_hidden_records":True}}
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(doc,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
print(json.dumps({"status":"PASS","scope":"ATDEMO","records":len(rows),"ids":[r["id"] for r in rows]}))
