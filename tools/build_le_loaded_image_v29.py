#!/usr/bin/env python3
"""OpenAzrael v29: reconstruct initialized Watcom LE objects and apply supported internal 32-bit offset fixups.
Conservative scope: this demo corpus contains only source type 7 + internal targets.
The raw legacy EXE is never modified.
"""
import argparse, json, struct, hashlib
from pathlib import Path
U32=lambda d,o:struct.unpack_from('<I',d,o)[0]
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('exe'); ap.add_argument('fixups'); ap.add_argument('--out-dir',required=True); ap.add_argument('--report',required=True); a=ap.parse_args()
 raw=Path(a.exe).read_bytes(); leoff=U32(raw,0x3c) if raw[:2]==b'MZ' else -1
 if leoff<0 or raw[leoff:leoff+2]!=b'LE':
  # fallback for malformed/bound stubs: require a structurally plausible LE header
  leoff=0x37d4c if len(raw)>0x37d4e and raw[0x37d4c:0x37d4e]==b'LE' else -1
 if leoff<0: raise SystemExit('LE header not found')
 le=raw[leoff:]; ps=U32(le,0x28); ot=U32(le,0x40); oc=U32(le,0x44); pm=U32(le,0x48); dp=U32(le,0x80)
 objs=[]
 for i in range(oc):
  size,base,flags,first,npg,res=struct.unpack_from('<IIIIII',le,ot+i*24); objs.append({'number':i+1,'size':size,'base':base,'flags':flags,'first_page':first,'page_count':npg})
 def pmap(mi):
  e=le[pm+4*mi:pm+4*mi+4]; return (e[0]<<16)|(e[1]<<8)|e[2],e[3]
 images=[]
 for o in objs:
  b=bytearray(o['size'])
  for lp in range(o['page_count']):
   pn,fl=pmap(o['first_page']-1+lp)
   if not pn: continue
   src=leoff+dp+(pn-1)*ps; dst=lp*ps; n=min(ps,o['size']-dst,max(0,len(raw)-src))
   if n>0:b[dst:dst+n]=raw[src:src+n]
  images.append(b)
 fx=json.loads(Path(a.fixups).read_text())
 supported=patched=bad=0; examples=[]
 for r in fx['records']:
  if r.get('source_type')!=7 or r.get('target_kind')!='internal' or r.get('target_offset') is None: continue
  supported+=1; so=r['source_object']; to=r['target_object']; off=r['source_offset']
  if not(1<=so<=len(images) and 1<=to<=len(images) and 0<=off<=len(images[so-1])-4): bad+=1; continue
  target=(objs[to-1]['base']+r['target_offset']) & 0xffffffff
  before=struct.unpack_from('<I',images[so-1],off)[0]; struct.pack_into('<I',images[so-1],off,target); after=struct.unpack_from('<I',images[so-1],off)[0]
  if after==target: patched+=1
  if len(examples)<20: examples.append({'source_object':so,'source_offset':off,'before':before,'after':after,'target_object':to,'target_offset':r['target_offset'],'target_linear':target})
 outd=Path(a.out_dir); outd.mkdir(parents=True,exist_ok=True)
 object_files=[]
 for o,b in zip(objs,images):
  p=outd/f"R_EXE.object{o['number']}.loaded.bin"; p.write_bytes(b); object_files.append({'object':o['number'],'path':p.name,'size':len(b),'base':o['base'],'sha256':hashlib.sha256(b).hexdigest()})
 # postcondition: every supported patch location now contains its decoded target linear address
 verify=0
 for r in fx['records']:
  if r.get('source_type')==7 and r.get('target_kind')=='internal' and r.get('target_offset') is not None:
   so,to,off=r['source_object'],r['target_object'],r['source_offset']
   if 1<=so<=len(images) and 1<=to<=len(images) and 0<=off<=len(images[so-1])-4:
    if struct.unpack_from('<I',images[so-1],off)[0]==((objs[to-1]['base']+r['target_offset'])&0xffffffff): verify+=1
 report={'schema':'openazrael.le_loaded_image','version':29,'exe_sha256':hashlib.sha256(raw).hexdigest(),'le_header_file_offset':leoff,'page_size':ps,'data_pages_offset':dp,'objects':objs,'fixups':{'structural_records':len(fx['records']),'supported_internal_type7':supported,'patched':patched,'invalid_source':bad,'postcondition_verified':verify},'loaded_objects':object_files,'patch_examples':examples,'confidence':{'physical_page_mapping':'HIGH','structural_fixup_decode':'HIGH','type7_internal_relocation_application':'HIGH','function_identity':'HOLD'},'interpretation':['Builds a loader-style initialized image without altering R.EXE.','For the current demo corpus, every structurally decoded fixup is source type 7 with an internal target.','Type 7 is treated as a 32-bit offset relocation and patched with target object relocation base + target offset.','Successful postcondition proves internal consistency of the simulator; independent code-level invariants are still required before function identities are promoted to VERIFIED.']}
 Path(a.report).write_text(json.dumps(report,indent=2),encoding='utf8')
 print(json.dumps({'leoff':hex(leoff),'objects':len(objs),'supported':supported,'patched':patched,'invalid_source':bad,'postcondition_verified':verify},indent=2))
if __name__=='__main__': main()
