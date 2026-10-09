from pathlib import Path
import re,hashlib,json,struct
src=Path(r"F:\Remaster Framework\source\Azrael's Tear\GAME\AZRAEL\R.EXE")
b=src.read_bytes()
strings=[(m.start(),m.group().decode("latin1","ignore")) for m in re.finditer(rb"[ -~]{4,}",b)]
need=("collision","tun_conn","object02","zq","zz","trimesh","wall","tunnel")
hits=[{"offset":o,"text":s} for o,s in strings if any(k in s.lower() for k in need)]
# Search for obvious little-endian ASCII pair immediates that could implement prefix checks.
patterns={
 "ZQ_ascii":b"ZQ","ZZ_ascii":b"ZZ","zq_ascii":b"zq","zz_ascii":b"zz",
 "imm_ZQ_le16":bytes.fromhex("515a"),"imm_ZZ_le16":bytes.fromhex("5a5a")
}
ph={}
for name,p in patterns.items():
    xs=[];start=0
    while True:
        i=b.find(p,start)
        if i<0:break
        xs.append(i);start=i+1
    ph[name]=xs[:500]
out={
 "schema":"OpenAzrael.RetailRExeStringPrefixAudit.v1",
 "source":str(src),"sha256":hashlib.sha256(b).hexdigest(),"bytes":len(b),
 "printable_hits":hits,"pattern_offsets":ph,
 "claim_limits":[
   "Raw string/pattern presence does not prove a collision filter.",
   "No runtime execution was performed.",
   "No source or repository file was modified."
 ]}
Path(__file__).with_name("scan.json").write_text(json.dumps(out,indent=2),encoding="utf-8")
print(json.dumps({"sha256":out["sha256"],"bytes":len(b),"printable_hits":hits[:80],
                  "pattern_counts":{k:len(v) for k,v in ph.items()}},indent=2))
