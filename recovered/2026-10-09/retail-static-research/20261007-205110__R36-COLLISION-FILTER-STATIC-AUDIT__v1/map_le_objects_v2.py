from pathlib import Path
import struct,hashlib,json
src=Path(r"F:\Remaster Framework\source\Azrael's Tear\GAME\AZRAEL\R.EXE")
raw=src.read_bytes()
LE_OFFSET=168188
def u32(b,o): return struct.unpack_from("<I",b,o)[0]
if raw[LE_OFFSET:LE_OFFSET+2]!=b"LE": raise SystemExit("LE signature mismatch")
le=raw[LE_OFFSET:]
page_size=u32(le,0x28);objtab=u32(le,0x40);objcnt=u32(le,0x44);pagemap=u32(le,0x48);datapages=u32(le,0x80)
objects=[]; blobs=[]
for oi in range(objcnt):
    off=objtab+oi*24
    size,base,flags,first_page,page_count,res=struct.unpack_from("<IIIIII",le,off)
    out=bytearray(size)
    for lp in range(page_count):
        ent=le[pagemap+4*(first_page-1+lp):pagemap+4*(first_page-1+lp)+4]
        phys=(ent[0]<<16)|(ent[1]<<8)|ent[2]
        if not phys: continue
        s=LE_OFFSET+datapages+(phys-1)*page_size
        dst=lp*page_size
        n=min(page_size,size-dst,max(0,len(raw)-s))
        if n>0: out[dst:dst+n]=raw[s:s+n]
    b=bytes(out);blobs.append(b)
    hits={}
    for needle in [b"NO_COLLISION",b"ICollisionManager",b"ZZ%04d",b"ZQ",b"ZZ"]:
        xs=[];p=0
        while True:
            p=b.find(needle,p)
            if p<0:break
            xs.append(p);p+=1
        if xs:hits[needle.decode("latin1")]=[{"object_offset":x,"linear":base+x} for x in xs]
    objects.append({"index":oi+1,"size":size,"base":base,"flags":flags,"first_page":first_page,
                    "page_count":page_count,"sha256":hashlib.sha256(b).hexdigest(),"hits":hits})
for i,b in enumerate(blobs,1):
    Path(__file__).with_name(f"object{i}.bin").write_bytes(b)
out={"schema":"OpenAzrael.RetailLEObjectMap.v2","exe_sha256":hashlib.sha256(raw).hexdigest(),
     "le_offset":LE_OFFSET,"page_size":page_size,"object_count":objcnt,"objects":objects}
Path(__file__).with_name("le_object_map_v2.json").write_text(json.dumps(out,indent=2),encoding="utf-8")
print(json.dumps(out,indent=2))
