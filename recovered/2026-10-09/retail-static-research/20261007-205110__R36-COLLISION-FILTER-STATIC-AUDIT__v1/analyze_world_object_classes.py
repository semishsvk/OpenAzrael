from pathlib import Path
import struct,json,collections,hashlib
src=Path(r"F:\Remaster Framework\source\Azrael's Tear\GAME\AZRAEL\WORLD.DAT")
b=src.read_bytes()
class R:
    def __init__(self,b):self.b=b;self.o=0
    def take(self,n):
        x=self.b[self.o:self.o+n]
        if len(x)!=n:raise ValueError("overrun")
        self.o+=n;return x
    def u16(self):return struct.unpack("<H",self.take(2))[0]
    def dyn(self):return [self.u16() for _ in range(self.u16())]
def c(x):return x.split(b"\0",1)[0].decode("latin1","replace")
r=R(b);r.take(30);n=r.u16();rows=[]
for i in range(n):
    start=r.o;ids=r.dyn();vals=[r.u16(),r.u16(),r.take(1)[0],r.u16(),r.take(1)[0],r.u16()]
    no=r.o;name=c(r.take(11));do=r.o;desc=c(r.take(30))
    rows.append({"index":i,"offset":start,"ids":ids,"fields":vals,"name":name,"description":desc})
door=[x for x in rows if x["description"].lower()=="door"]
wall=[x for x in rows if x["description"].lower()=="wall"]
tun=[x for x in rows if x["name"].lower().startswith("tun_conn")]
r36=[x for x in rows if "r36" in x["name"].lower() or "r36" in x["description"].lower()]
target=next(x for x in rows if x["name"].lower()=="tun_conn01")
lo=max(0,target["index"]-8);hi=min(len(rows),target["index"]+9)
out={
 "schema":"OpenAzrael.RetailWorldObjectClassAudit.v1","world_sha256":hashlib.sha256(b).hexdigest(),
 "section0_count":n,"door_count":len(door),"wall_count":len(wall),
 "tun_conn_records":tun,
 "tun_conn_descriptions":dict(collections.Counter(x["description"] for x in tun)),
 "tun_conn_field_patterns":[{"fields":list(k),"count":v} for k,v in collections.Counter(tuple(x["fields"]) for x in tun).items()],
 "tun_conn01_neighbors":rows[lo:hi],
 "r36_named_records":r36,
 "identity_bridge_status":"HOLD: WORLD object name is not sufficient to choose among repeated XAF object names.",
 "safe_claim":"WORLD confirms at least one runtime tun_conn01 object is typed Door, and all WORLD tun_conn* records found are typed Door. It does not yet bind that record to R36.XAF."
}
Path(__file__).with_name("world_object_class_audit.json").write_text(json.dumps(out,indent=2),encoding="utf-8")
print(json.dumps(out,indent=2))
