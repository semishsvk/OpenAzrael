#!/usr/bin/env python3
from pathlib import Path
import argparse,hashlib,json,struct,sys
EXPECTED_SHA="381e4f5c61e4bb8c27f06b1944e6673bbebc39ca219cc08fb9f948da2ca37c00"
LE_FILE_OFFSET=0x37D4C
def u32(b,o): return struct.unpack_from("<I",b,o)[0]
def parse(path):
 b=path.read_bytes()
 if hashlib.sha256(b).hexdigest()!=EXPECTED_SHA: raise SystemExit("CANONICAL_R_EXE_HASH_MISMATCH")
 h=LE_FILE_OFFSET
 if b[h:h+2]!=b"LE" or b[h+2:h+4]!=b"\0\0": raise SystemExit("LE_HEADER_MISMATCH")
 page_size=u32(b,h+40); pages=u32(b,h+20); objtab=u32(b,h+64); objcnt=u32(b,h+68); objmap=u32(b,h+72); datapage=u32(b,h+128)
 objects=[]
 for i in range(objcnt):
  vsize,base,flags,pmi,pc,res=struct.unpack_from("<6I",b,h+objtab+i*24)
  objects.append({"index":i+1,"virtual_size":vsize,"reloc_base":base,"flags":flags,"page_map_index":pmi,"page_count":pc})
 pm=[]
 for i in range(pages):
  x=b[h+objmap+i*4:h+objmap+i*4+4]; pm.append({"physical_page":int.from_bytes(x[:3],"big"),"flags":x[3]})
 data_file=h+datapage
 def map_off(objidx,off):
  o=objects[objidx-1]; pi=off//page_size
  if pi>=o["page_count"]: raise ValueError("OBJECT_OFFSET_OUT_OF_RANGE")
  ent=pm[o["page_map_index"]-1+pi]
  return data_file+(ent["physical_page"]-1)*page_size+(off%page_size)
 entry_obj=u32(b,h+24); entry_off=u32(b,h+28); entry_file=map_off(entry_obj,entry_off)
 return {"schema":"openazrael.le_mapping","version":184,"source_sha256":EXPECTED_SHA,"le_header_file_offset":h,
 "module_pages":pages,"page_size":page_size,"object_count":objcnt,"objects":objects,
 "data_pages_header_relative_offset":datapage,"data_pages_file_offset":data_file,
 "entry":{"object":entry_obj,"offset":entry_off,"file_offset":entry_file},
 "fixup":{"section_size":u32(b,h+48),"page_table_header_relative":u32(b,h+104),"record_table_header_relative":u32(b,h+108)}}
 # Parse variable-length LE fixups and require exact per-page boundaries.
 fp=h+u32(b,h+104); fr=h+u32(b,h+108)
 po=[u32(b,fp+4*i) for i in range(pages+1)]
 total=0; types={}; targets={}
 for pg in range(pages):
  pos,end=fr+po[pg],fr+po[pg+1]
  while pos<end:
   start=pos; src=b[pos]; flags=b[pos+1]; pos+=2
   if src&0x20: cnt=b[pos]; pos+=1
   else: pos+=2; cnt=None
   targ=flags&3; osz=2 if flags&0x40 else 1
   if targ==0:
    pos+=osz
    if (src&0x0f)!=2: pos+=4 if flags&0x10 else 2
   elif targ==1:
    pos+=osz
    pos+=1 if flags&0x80 else (4 if flags&0x10 else 2)
   elif targ==2:
    pos+=osz; pos+=4 if flags&0x10 else 2
   else:
    pos+=osz
   if flags&0x04: pos+=4 if flags&0x20 else 2
   if src&0x20: pos+=2*cnt
   if pos>end or pos<=start: raise SystemExit("FIXUP_RECORD_BOUNDARY_MISMATCH")
   total+=1; types[str(src&0x0f)]=types.get(str(src&0x0f),0)+1; targets[str(targ)]=targets.get(str(targ),0)+1
  if pos!=end: raise SystemExit("FIXUP_PAGE_BOUNDARY_MISMATCH")
 result["fixup"].update({"page_count":pages,"record_count":total,"source_type_counts":types,"target_type_counts":targets,"record_bytes":po[-1]})
 return result
def main():
 a=argparse.ArgumentParser();a.add_argument("exe",type=Path);x=a.parse_args();print(json.dumps(parse(x.exe),indent=2))
if __name__=="__main__": main()
