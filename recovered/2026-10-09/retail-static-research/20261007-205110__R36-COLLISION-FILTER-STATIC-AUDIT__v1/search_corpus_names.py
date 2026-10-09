from pathlib import Path
import hashlib,json
root=Path(r"F:\Remaster Framework\source\Azrael's Tear\GAME\AZRAEL")
needles=[b"tun_conn01",b"tun_conn02",b"tun_connec",b"Object02",b"NO_COLLISION"]
rows=[]
for p in sorted(root.rglob("*")):
    if not p.is_file(): continue
    try:
        data=p.read_bytes()
    except Exception: continue
    found={}
    low=data.lower()
    for n in needles:
        xs=[]; start=0; key=n.decode("ascii")
        nn=n.lower()
        while True:
            i=low.find(nn,start)
            if i<0:break
            xs.append(i);start=i+1
        if xs:found[key]=xs
    if found:
        rows.append({"file":str(p.relative_to(root)),"size":len(data),
                     "sha256":hashlib.sha256(data).hexdigest(),"matches":found})
out={"schema":"OpenAzrael.RetailCorpusNameSearch.v1","root":str(root),
     "needles":[n.decode() for n in needles],"files_with_matches":rows,
     "claim_limits":["String presence is structural evidence only; absence does not prove no binary/ordinal binding."]}
Path(__file__).with_name("corpus_name_search.json").write_text(json.dumps(out,indent=2),encoding="utf-8")
print(json.dumps(out,indent=2))
