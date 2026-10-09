from pathlib import Path
import struct,json,hashlib
from capstone import Cs,CS_ARCH_X86,CS_MODE_32
root=Path(__file__).parent
raw=Path(r"F:\Remaster Framework\source\Azrael's Tear\GAME\AZRAEL\R.EXE").read_bytes()
LEOFF=168188
le=raw[LEOFF:]
U16=lambda d,o:struct.unpack_from("<H",d,o)[0]
U32=lambda d,o:struct.unpack_from("<I",d,o)[0]
I16=lambda d,o:struct.unpack_from("<h",d,o)[0]
npages=U32(le,0x14);ps=U32(le,0x28);ot=U32(le,0x40);oc=U32(le,0x44);fpt=U32(le,0x68);frt=U32(le,0x6c)
objs=[]
for i in range(oc):
    size,base,flags,first,npg,_=struct.unpack_from("<IIIIII",le,ot+i*24)
    objs.append({"number":i+1,"size":size,"base":base,"first_page":first,"page_count":npg})
pages=[U32(le,fpt+4*i) for i in range(npages+1)]
def source_obj(pg0):
    p=pg0+1
    for o in objs:
        if o["first_page"]<=p<o["first_page"]+o["page_count"]:
            return o,(p-o["first_page"])*ps
    return None,None
records=[]
for pg in range(npages):
    p=frt+pages[pg];end=frt+pages[pg+1]
    while p<end:
        rs=p;typ,fl=le[p],le[p+1];p+=2;islist=bool(typ&0x20)
        if islist: ns=le[p];p+=1;srcs=[]
        else: ns=0;srcs=[I16(le,p)];p+=2
        ordsz=2 if fl&0x40 else 1;tk=fl&3
        if tk==0:
            obj=U16(le,p) if ordsz==2 else le[p];p+=ordsz;off=None
            if (typ&0xf)!=2:
                off=U32(le,p) if fl&0x10 else U16(le,p);p+=4 if fl&0x10 else 2
            add=None
            if fl&4:add=U32(le,p) if fl&0x20 else U16(le,p);p+=4 if fl&0x20 else 2
            target={"kind":"internal","object":obj,"offset":off,"additive":add}
        elif tk==1:
            mod=U16(le,p) if ordsz==2 else le[p];p+=ordsz
            proc=le[p] if fl&0x80 else (U32(le,p) if fl&0x10 else U16(le,p));p+=1 if fl&0x80 else (4 if fl&0x10 else 2)
            if fl&4:p+=4 if fl&32 else 2
            target={"kind":"import_ordinal","module":mod,"proc":proc}
        elif tk==2:
            mod=U16(le,p) if ordsz==2 else le[p];p+=ordsz
            name=U32(le,p) if fl&16 else U16(le,p);p+=4 if fl&16 else 2
            if fl&4:p+=4 if fl&32 else 2
            target={"kind":"import_name","module":mod,"name_offset":name}
        else:
            p+=ordsz
            if fl&4:p+=4 if fl&32 else 2
            target={"kind":"entry"}
        if islist:
            srcs=[I16(le,p+2*i) for i in range(ns)];p+=2*ns
        so,pbase=source_obj(pg)
        records.append({"page":pg+1,"record_le_offset":rs,"raw":le[rs:p].hex(),
          "source_type":typ&15,"source_flags":typ,"target_flags":fl,"sources":srcs,
          "source_object":so["number"] if so else None,"page_object_base":pbase,"target":target})
# target exact collision-manager debug names
targets={0x744:"ICollisionManager",0x776:"UpdateWorldFaces"}
hits=[]
blobs={1:(root/"object1.bin").read_bytes(),2:(root/"object2.bin").read_bytes()}
md=Cs(CS_ARCH_X86,CS_MODE_32)
for r in records:
    t=r["target"]
    if t.get("kind")!="internal" or t.get("object")!=2 or t.get("offset") not in targets:continue
    so=r["source_object"];baseoff=r["page_object_base"]
    for sr in r["sources"]:
        off=baseoff+sr
        item={**r,"source_relative_in_object":off,"target_label":targets[t["offset"]]}
        if so in blobs and -128<=off<len(blobs[so])+128:
            b=blobs[so];lo=max(0,off-96);hi=min(len(b),off+128);base=objs[so-1]["base"]
            item["context_hex"]=b[lo:hi].hex()
            item["disasm"]=[{"va":i.address,"off":i.address-base,"bytes":i.bytes.hex(),"op":i.mnemonic+" "+i.op_str}
                for i in md.disasm(b[lo:hi],base+lo) if base+off-72<=i.address<=base+off+96]
        hits.append(item)
out={"schema":"OpenAzrael.RetailCollisionFixupXrefs.v1","exe_sha256":hashlib.sha256(raw).hexdigest(),
 "le_offset":LEOFF,"fixup_record_count":len(records),"objects":objs,"hits":hits,
 "target_offsets":{"ICollisionManager":0x744,"UpdateWorldFaces":0x776},
 "claim_limits":["Canonical LE target object+offset is trusted; flat relocation value remains HOLD unless independently validated."]}
(root/"collision_fixup_xrefs.json").write_text(json.dumps(out,indent=2),encoding="utf-8")
print(json.dumps({"fixup_record_count":len(records),"hit_count":len(hits),"hits":hits},indent=2))
