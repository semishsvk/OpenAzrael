from pathlib import Path
import struct,json
from capstone import Cs,CS_ARCH_X86,CS_MODE_32
root=Path(__file__).parent
obj=(root/"object1.bin").read_bytes()
BASE=0x10000
targets={
 "NO_COLLISION_objoff":1188698,
 "NO_COLLISION_linear":BASE+1188698,
 "ZZfmt_objoff":1188571,
 "ZZfmt_linear":BASE+1188571,
}
out={}
md=Cs(CS_ARCH_X86,CS_MODE_32)
for name,val in targets.items():
    pat=struct.pack("<I",val)
    hits=[];p=0
    while True:
        p=obj.find(pat,p)
        if p<0:break
        start=max(0,p-48);chunk=obj[start:min(len(obj),p+64)]
        ins=[]
        for i in md.disasm(chunk,BASE+start):
            if BASE+p-40<=i.address<=BASE+p+48:
                ins.append({"va":i.address,"bytes":i.bytes.hex(),"op":i.mnemonic+" "+i.op_str})
        hits.append({"object_offset":p,"linear":BASE+p,"context_hex":chunk.hex(),"disasm":ins})
        p+=1
    out[name]={"value":val,"hits":hits}
Path(__file__).with_name("xref_collision_strings.json").write_text(json.dumps(out,indent=2),encoding="utf-8")
print(json.dumps({k:{"value":v["value"],"hit_count":len(v["hits"]),
  "hits":[{"object_offset":h["object_offset"],"linear":h["linear"],"disasm":h["disasm"]} for h in v["hits"][:20]]} for k,v in out.items()},indent=2))
