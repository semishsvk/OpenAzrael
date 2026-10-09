from pathlib import Path
import json
from capstone import Cs,CS_ARCH_X86,CS_MODE_32
root=Path(__file__).parent; obj=(root/"object1.bin").read_bytes(); BASE=0x10000
md=Cs(CS_ARCH_X86,CS_MODE_32)
rows=[]
for ins in md.disasm(obj,BASE):
    if ins.mnemonic in ("cmp","test") and ("0x5a" in ins.op_str.lower() or "0x51" in ins.op_str.lower()):
        rows.append({"va":ins.address,"off":ins.address-BASE,"bytes":ins.bytes.hex(),"op":ins.mnemonic+" "+ins.op_str})
clusters=[]
for i,a in enumerate(rows):
    near=[b for b in rows if 0<=b["va"]-a["va"]<=64]
    vals=" ".join(b["op"].lower() for b in near)
    if "0x5a" in vals and "0x51" in vals:
        clusters.append({"start":a["va"],"rows":near})
# dedupe by first address
seen=set(); uniq=[]
for c in clusters:
    key=tuple(r["va"] for r in c["rows"])
    if key not in seen: seen.add(key); uniq.append(c)
out={"schema":"OpenAzrael.RetailPrefixByteSequenceScan.v1","candidate_comparisons":rows,"paired_clusters":uniq}
(root/"prefix_byte_sequences.json").write_text(json.dumps(out,indent=2),encoding="utf-8")
print(json.dumps({"comparison_count":len(rows),"paired_cluster_count":len(uniq),"paired_clusters":uniq[:50]},indent=2))
