from pathlib import Path
import json,hashlib,re,struct,collections
src=Path(r"F:\Remaster Framework\source\Azrael's Tear\GAME\AZRAEL\OBJECTS.DAT")
b=src.read_bytes(); off=b.lower().find(b"tun_conn02")
if off<0: raise SystemExit("tun_conn02 not found")
lo=max(0,off-1024);hi=min(len(b),off+2048);chunk=b[lo:hi]
strings=[]
for m in re.finditer(rb"[ -~]{3,}\x00",chunk):
    strings.append({"offset":lo+m.start(),"text":m.group()[:-1].decode("latin1","ignore")})
# Find all likely record spacings around nul-terminated object-ish strings.
allstr=[]
for m in re.finditer(rb"[A-Za-z_][A-Za-z0-9_ -]{2,30}\x00",b):
    allstr.append((m.start(),m.group()[:-1].decode("latin1","ignore")))
near=[{"offset":o,"text":s,"delta_from_target":o-off} for o,s in allstr if abs(o-off)<4096]
# repeating distances in local string starts may indicate record slots
deltas=collections.Counter(b[0]-a[0] for a,b in zip(allstr,allstr[1:]) if 0<b[0]-a[0]<512)
out={"schema":"OpenAzrael.RetailObjectsDatTunConnProbe.v1","source":str(src),
 "sha256":hashlib.sha256(b).hexdigest(),"bytes":len(b),"target_offset":off,
 "window_strings":strings,"nearby_objectlike_strings":near,
 "common_adjacent_string_deltas":deltas.most_common(30),
 "window_hex":chunk.hex(),
 "claim_limits":["No OBJECTS.DAT record grammar is asserted from string spacing alone."]}
Path(__file__).with_name("objects_dat_tunconn_probe.json").write_text(json.dumps(out,indent=2),encoding="utf-8")
print(json.dumps({k:out[k] for k in ["sha256","bytes","target_offset","window_strings","nearby_objectlike_strings","common_adjacent_string_deltas"]},indent=2))
