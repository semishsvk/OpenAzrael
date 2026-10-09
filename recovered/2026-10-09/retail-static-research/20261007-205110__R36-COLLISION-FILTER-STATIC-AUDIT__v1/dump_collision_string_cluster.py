from pathlib import Path
import re,json
root=Path(__file__).parent
obj=(root/"object1.bin").read_bytes()
lo=1187600;hi=min(len(obj),1190000)
rows=[]
for m in re.finditer(rb"[ -~]{3,}\x00",obj[lo:hi]):
    off=lo+m.start()
    rows.append({"object_offset":off,"linear":0x10000+off,"text":m.group()[:-1].decode("latin1","ignore")})
Path(__file__).with_name("collision_string_cluster.json").write_text(json.dumps(rows,indent=2),encoding="utf-8")
print(json.dumps(rows,indent=2))
