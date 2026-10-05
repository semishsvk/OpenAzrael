from pathlib import Path
import json,hashlib,sys,re
src=Path(sys.argv[1]); out=Path(sys.argv[2])
raw=src.read_bytes(); L=raw.decode("latin1").replace("\r\n","\n").splitlines()
def ints(s): return [int(x) for x in s.split(",")]
def flag(s):
    v=ints(s); return {"type":v[0],"args":v[1:],"raw":s}
def parse_family(i,name):
    # i points at family name. Header is family metadata followed by record count.
    i+=1
    header=[]
    # 1A has three metadata integers before count; 1B has one.
    meta_n=2 if name=="1A" else 1
    for _ in range(meta_n): header.append(int(L[i])); i+=1
    count=int(L[i]); i+=1
    rows=[]
    for _ in range(count):
        rid=L[i].strip(); i+=1
        pre_n=int(L[i]); i+=1
        pre=[flag(L[i+j].strip()) for j in range(pre_n)]; i+=pre_n
        act_n=int(L[i]); i+=1
        actions=[flag(L[i+j].strip()) for j in range(act_n)]; i+=act_n
        player=L[i]; i+=1
        # response envelope: three numeric fields, response text, marker,
        # then three numeric tail fields. Preserve all controls.
        response_head=[int(L[i+j]) for j in range(3)]; i+=3
        response=L[i]; i+=1
        marker=L[i].strip(); i+=1
        if marker != "Ni%s_%s"%(name,rid):
            raise ValueError(f"marker mismatch {name}/{rid}: {marker}")
        response_tail=[int(L[i+j]) for j in range(3)]; i+=3
        rows.append({"id":rid,"source_marker":marker,"prerequisites":pre,"actions":actions,
                     "player_text":player,"response_control":response_head,
                     "niamh_text":response,"tail_control":response_tail})
    return i,{"header":header,"declared_records":count,"records":rows}
families={}; i=1 # first line = family count
for fam in ["1A","1B"]:
    while i<len(L) and L[i].strip()!=fam: i+=1
    i,data=parse_family(i,fam); families[fam]=data
doc={"schema":"openazrael.conversation_ir","version":210,"status":"SOURCE_GRAMMAR_PARSED",
"source":{"file":"NIAMH.DAT","bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest()},
"character":"Niamh","families":families,
"flag_semantics":{"record_shape":"type + 0..4 integer args","types":"0..8 source parser domain","meaning":"HOLD pending canonical R.EXE/runtime corroboration"},
"policy":{"unknown_flag_semantics_not_invented":True,"missing_answer_text_not_invented":True,"do_not_display_hidden_records":True}}
out.write_text(json.dumps(doc,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
print(json.dumps({"status":"PASS","families":{k:len(v["records"]) for k,v in families.items()},
"typed_prerequisites":sum(len(r["prerequisites"]) for f in families.values() for r in f["records"]),
"typed_actions":sum(len(r["actions"]) for f in families.values() for r in f["records"])}))
