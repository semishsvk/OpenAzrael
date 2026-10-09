from pathlib import Path
import struct,json,hashlib
src=Path(r"F:\Remaster Framework\source\Azrael's Tear\GAME\AZRAEL\R.EXE")
raw=src.read_bytes()
def u32(b,o): return struct.unpack_from("<I",b,o)[0]
c=[]
p=0
while True:
    p=raw.find(b"LE",p)
    if p<0:break
    ok=False; fields={}
    try:
        le=raw[p:]
        page=u32(le,0x28); objtab=u32(le,0x40); objcnt=u32(le,0x44); pagemap=u32(le,0x48); datapages=u32(le,0x80)
        ok=(page in (0x1000,0x2000,0x4000,0x10000) and 0<objcnt<64 and
            0<objtab<len(le) and 0<pagemap<len(le) and 0<datapages<len(le) and
            objtab+objcnt*24<=len(le))
        fields=dict(page_size=page,object_table=objtab,object_count=objcnt,page_map=pagemap,data_pages=datapages)
    except Exception as e: fields={"error":type(e).__name__}
    c.append({"offset":p,"valid":ok,**fields})
    p+=2
out={"schema":"OpenAzrael.RetailLECandidateScan.v1","exe_sha256":hashlib.sha256(raw).hexdigest(),"candidates":c}
Path(__file__).with_name("le_candidates.json").write_text(json.dumps(out,indent=2),encoding="utf-8")
print(json.dumps(out,indent=2))
