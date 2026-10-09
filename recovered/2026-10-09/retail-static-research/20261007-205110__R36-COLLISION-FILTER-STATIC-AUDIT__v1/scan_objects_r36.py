from pathlib import Path
import re,json,hashlib
src=Path(r"F:\Remaster Framework\source\Azrael's Tear\GAME\AZRAEL\OBJECTS.DAT")
b=src.read_bytes()
rows=[]
for m in re.finditer(rb"[ -~]{3,}\x00",b):
    s=m.group()[:-1].decode("latin1","ignore")
    if "R36" in s.upper() or "TUN" in s.upper() or "DOOR" in s.upper():
        rows.append({"offset":m.start(),"text":s})
out={"schema":"OpenAzrael.RetailObjectsR36StringAudit.v1",
 "sha256":hashlib.sha256(b).hexdigest(),
 "r36_or_tunnel_or_door_strings":rows,
 "r36_count":sum("R36" in r["text"].upper() for r in rows),
 "tun_count":sum("TUN" in r["text"].upper() for r in rows),
 "claim_limits":["String matches do not alone bind an XAF object to runtime behavior."]}
Path(__file__).with_name("objects_r36_strings.json").write_text(json.dumps(out,indent=2),encoding="utf-8")
print(json.dumps({"r36_count":out["r36_count"],"tun_count":out["tun_count"],
 "r36":[r for r in rows if "R36" in r["text"].upper()],
 "tunnel":[r for r in rows if "TUN" in r["text"].upper()][:80]},indent=2))
