from pathlib import Path
import json,struct,re
root=Path(__file__).parent
o1=(root/"object1.bin").read_bytes()
o2=(root/"object2.bin").read_bytes()
B1=0x10000;B2=0x140000
needle=b"ICollisionManager"
off=o2.find(needle)
if off<0:raise SystemExit("missing ICollisionManager")
lo=max(0,off-512);hi=min(len(o2),off+1024)
strings=[]
for m in re.finditer(rb"[ -~]{3,}\x00",o2[lo:hi]):
    strings.append({"off":lo+m.start(),"linear":B2+lo+m.start(),"text":m.group()[:-1].decode("latin1","ignore")})
# Scan 32-bit values in data object pointing to the class string, and code object immediates pointing to those data slots/string.
ptrs=[]
for p in range(0,len(o2)-3):
    v=struct.unpack_from("<I",o2,p)[0]
    if v in (B2+off,off):
        ptrs.append({"data_off":p,"data_linear":B2+p,"value":v})
refs=[]
targets={B2+off,off}|{x["data_linear"] for x in ptrs}|{x["data_off"] for x in ptrs}
for p in range(0,len(o1)-3):
    v=struct.unpack_from("<I",o1,p)[0]
    if v in targets:
        refs.append({"code_off":p,"code_linear":B1+p,"value":v,"bytes":o1[max(0,p-20):p+24].hex()})
out={"schema":"OpenAzrael.RetailCollisionManagerRTTIProbe.v1","string_off":off,
 "string_linear":B2+off,"nearby_strings":strings,"data_pointer_hits":ptrs,"code_reference_candidates":refs,
 "claim_limits":["Pointer candidates require loader/fixup validation; object2 may use relocatable values rather than linear addresses."]}
(root/"collision_manager_rtti.json").write_text(json.dumps(out,indent=2),encoding="utf-8")
print(json.dumps(out,indent=2))
