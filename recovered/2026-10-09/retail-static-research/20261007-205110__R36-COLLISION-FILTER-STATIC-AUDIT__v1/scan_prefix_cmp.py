from pathlib import Path
import json
from capstone import Cs,CS_ARCH_X86,CS_MODE_32
root=Path(__file__).parent
obj=(root/"object1.bin").read_bytes()
BASE=0x10000
md=Cs(CS_ARCH_X86,CS_MODE_32)
hits=[]
for ins in md.disasm(obj,BASE):
    text=(ins.mnemonic+" "+ins.op_str).lower()
    # ASCII pair integer values: ZQ = 0x515a, ZZ = 0x5a5a.
    if "0x515a" in text or "0x5a5a" in text:
        hits.append({"va":ins.address,"object_offset":ins.address-BASE,
                     "bytes":ins.bytes.hex(),"op":ins.mnemonic+" "+ins.op_str})
out={"schema":"OpenAzrael.RetailPrefixCompareScan.v1",
     "targets":{"ZQ":"0x515a","ZZ":"0x5a5a"},"hits":hits,
     "claim_limits":["Linear disassembly candidates require local control-flow validation.",
                     "No match would not prove absence of an indirect library/string compare."]}
(root/"prefix_cmp_scan.json").write_text(json.dumps(out,indent=2),encoding="utf-8")
print(json.dumps(out,indent=2))
