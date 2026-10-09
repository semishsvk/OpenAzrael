from pathlib import Path
import struct,re,json,hashlib,collections
src=Path(r"F:\Remaster Framework\source\Azrael's Tear\GAME\AZRAEL\OBJECTS.DAT")
b=src.read_bytes()
count=struct.unpack_from("<H",b,0)[0]
assert len(b)==2+count*603,(len(b),count)
rows=[]
for i in range(count):
    start=2+i*603
    rec=b[start:start+603]
    strings=[]
    # printable runs; retain relative offsets
    for m in re.finditer(rb"[ -~]{3,}\x00",rec):
        strings.append({"rel":m.start(),"abs":start+m.start(),"text":m.group()[:-1].decode("latin1","ignore")})
    rows.append({"index":i,"start":start,"sha256":hashlib.sha256(rec).hexdigest(),"strings":strings})
targets=[]
for r in rows:
    texts=[x["text"] for x in r["strings"]]
    joined="\n".join(texts).upper()
    if ("R36" in joined or "TUN_CONN" in joined or "R49TUNNELDOOR" in joined):
        targets.append(r)
# summarize recurring string offsets/classes
offset_text=collections.defaultdict(collections.Counter)
for r in rows:
    for s in r["strings"]:
        offset_text[s["rel"]][s["text"]]+=1
common=[{"rel":rel,"records":sum(c.values()),"top":c.most_common(8)}
        for rel,c in offset_text.items() if sum(c.values())>=10]
common=sorted(common,key=lambda x:(-x["records"],x["rel"]))
out={"schema":"OpenAzrael.RetailObjectsDat603.v1","source":str(src),
 "sha256":hashlib.sha256(b).hexdigest(),"count":count,"record_size":603,"header_bytes":2,
 "targets":targets,"common_string_offsets":common[:80],
 "claim":"OBJECTS.DAT is structurally parsed as u16 record count followed by fixed 603-byte records; target strings shown belong to the same record.",
 "claim_limits":["String field meanings remain structural until bound to original reader code."]}
Path(__file__).with_name("objects_fixed603.json").write_text(json.dumps(out,indent=2),encoding="utf-8")
print(json.dumps({"count":count,"record_size":603,
 "targets":[{"index":r["index"],"start":r["start"],"strings":r["strings"]} for r in targets],
 "common_string_offsets":common[:30]},indent=2))
