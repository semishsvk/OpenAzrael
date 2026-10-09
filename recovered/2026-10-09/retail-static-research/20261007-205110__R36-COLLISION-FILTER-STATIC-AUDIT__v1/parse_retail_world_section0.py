from pathlib import Path
import struct,json,hashlib
src=Path(r"F:\Remaster Framework\source\Azrael's Tear\GAME\AZRAEL\WORLD.DAT")
data=src.read_bytes()
class R:
    def __init__(self,b): self.b=b; self.o=0
    def take(self,n):
        if n<0 or self.o+n>len(self.b): raise ValueError((self.o,n,len(self.b)))
        x=self.b[self.o:self.o+n];self.o+=n;return x
    def u16(self): return struct.unpack("<H",self.take(2))[0]
    def dyn(self):
        n=self.u16();return [self.u16() for _ in range(n)]
def c(raw): return raw.split(b"\0",1)[0].decode("latin1","replace")
r=R(data); header=r.take(30); n0=r.u16(); rows=[]
for idx in range(n0):
    start=r.o
    ids=r.dyn()
    f06=r.u16(); f08=r.u16(); f0a=r.take(1)[0]; f0b=r.u16(); f0d=r.take(1)[0]; f0e=r.u16()
    name_off=r.o; name=c(r.take(11))
    desc_off=r.o; desc=c(r.take(30))
    rows.append({"index":idx,"record_stream_offset":start,"ids":ids,
       "serialized_fields":{"f06":f06,"f08":f08,"f0a":f0a,"f0b":f0b,"f0d":f0d,"f0e":f0e},
       "name_offset":name_off,"name":name,"description_offset":desc_off,"description":desc})
targets=[x for x in rows if x["name"].lower() in {"tun_conn01","tun_conn02","object02"}]
# Continue remaining sections only to independently validate exact EOF grammar.
counts=[n0]
n1=r.u16();counts.append(n1)
for _ in range(n1): r.take(2);r.take(2);r.take(11);r.dyn()
n2=r.u16();counts.append(n2)
for _ in range(n2): r.take(9);r.dyn();r.dyn()
n3=r.u16();counts.append(n3)
for _ in range(n3): r.take(2);r.take(2);r.dyn()
n4=r.u16();counts.append(n4);n5=r.u16();counts.append(n5)
n6=r.u16();counts.append(n6)
for _ in range(n6):
    r.take(2);nodes=r.u16()
    for __ in range(nodes):
        objs=r.u16()
        for ___ in range(objs):
            r.take(2); c37=r.u16();r.take(37*c37); c27=r.u16();r.take(27*c27)
out={"schema":"OpenAzrael.RetailWorldSection0.v1","source":str(src),
 "sha256":hashlib.sha256(data).hexdigest(),"header_hex":header.hex(),
 "section_counts":counts,"section0_count":n0,"targets":targets,
 "target_count":len(targets),"end_offset":r.o,"file_size":len(data),
 "consumed_exactly_to_eof":r.o==len(data),
 "claim":"Names and descriptions listed in each target are fields of the same serialized section-0 runtime object record.",
 "claim_limits":["Section-0 identity/type fields do not alone prove collision membership or door behavior."]}
Path(__file__).with_name("retail_world_section0.json").write_text(json.dumps(out,indent=2),encoding="utf-8")
print(json.dumps(out,indent=2))
