from pathlib import Path
import json,hashlib,sys
src=Path(sys.argv[1]); out=Path(sys.argv[2])
raw=src.read_bytes(); L=raw.decode("latin1").replace("\r\n","\n").splitlines()
if len(raw)!=342 or hashlib.sha256(raw).hexdigest()!="e3f0b14b64682f0e621f7f52fb998ccf8ddba4febd0ac0df4aa201f371939f71":
    raise ValueError("canonical ATDEMO NIAMH.DAT fingerprint mismatch")
i=0
if L[i].strip()!="1": raise ValueError("family count")
i+=1
if L[i].strip()!="1A": raise ValueError("expected demo 1A")
i+=1
header=[int(L[i]),int(L[i+1])]; i+=2
count=int(L[i]); i+=1
# ATDEMO 1A has one family-level control word after the declared count.
family_control=int(L[i]); i+=1
rows=[]
for _ in range(count):
    rid=L[i].strip(); i+=1
    pre_n=int(L[i]); i+=1
    pre=[L[i+j].strip() for j in range(pre_n)]; i+=pre_n
    act_n=int(L[i]); i+=1
    actions=[L[i+j].strip() for j in range(act_n)]; i+=act_n
    player=L[i]; i+=1
    response_control=[int(L[i+j]) for j in range(3)]; i+=3
    response=L[i]; i+=1
    marker=L[i].strip(); i+=1
    if marker!=f"Ni1A_{rid}": raise ValueError((rid,marker))
    tail=[int(L[i+j]) for j in range(3)]; i+=3
    rows.append({"id":rid,"source_marker":marker,"prerequisites":pre,"actions":actions,
                 "player_text":player,"response_control":response_control,
                 "niamh_text":response,"tail_control":tail})
if [r["id"] for r in rows]!=["30","999","A"]: raise ValueError("unexpected demo 1A record set")
doc={"schema":"openazrael.demo.conversation_ir","version":253,"status":"ATDEMO_SOURCE_PARSED","scope":"ATDEMO",
     "source":{"file":"NIAMH.DAT","bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest()},
     "character":"Niamh","families":{"1A":{"header":header,"declared_records":count,"records":rows}},
     "policy":{"retail_1b_not_required":True,"do_not_display_hidden_records":True}}
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(doc,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
print(json.dumps({"status":"PASS","version":253,"families":{"1A":len(rows)},"sha256":doc["source"]["sha256"]}))
