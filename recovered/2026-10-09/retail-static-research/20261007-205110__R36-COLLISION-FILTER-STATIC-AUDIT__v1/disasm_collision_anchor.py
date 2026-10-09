from pathlib import Path
import json,struct
from capstone import Cs,CS_ARCH_X86,CS_MODE_32
root=Path(__file__).parent
o1=(root/"object1.bin").read_bytes();o2=(root/"object2.bin").read_bytes()
B1=0x10000;B2=0x140000
md=Cs(CS_ARCH_X86,CS_MODE_32)
anchors={"ICollisionManager":o2.find(b"ICollisionManager"),"UpdateWorldFaces":o2.find(b"UpdateWorldFaces")}
# Candidate raw 32-bit references to relative object2 offsets or linear addresses.
refs={}
for name,off in anchors.items():
    vals=[off,B2+off]
    hh=[]
    for val in vals:
        pat=struct.pack("<I",val);p=0
        while True:
            p=o1.find(pat,p)
            if p<0:break
            start=max(0,p-96);end=min(len(o1),p+128)
            ins=[{"va":i.address,"off":i.address-B1,"bytes":i.bytes.hex(),"op":i.mnemonic+" "+i.op_str}
                 for i in md.disasm(o1[start:end],B1+start)
                 if B1+p-80<=i.address<=B1+p+96]
            hh.append({"target_value":val,"ref_off":p,"ref_va":B1+p,"disasm":ins})
            p+=1
    refs[name]=hh
out={"schema":"OpenAzrael.RetailCollisionAnchorDisasm.v1","anchors":anchors,"refs":refs}
(root/"collision_anchor_disasm.json").write_text(json.dumps(out,indent=2),encoding="utf-8")
print(json.dumps(out,indent=2))
