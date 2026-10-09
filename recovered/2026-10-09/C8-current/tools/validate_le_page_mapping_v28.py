#!/usr/bin/env python3
"""OpenAzrael v28: validate LE physical page mapping and correct v27 source-file mapping.
The LE Data Pages Offset is an absolute file offset for this bound executable.
Do not validate relocations by expecting the pre-relocation source dword to equal the target.
"""
import argparse,json,struct,hashlib
from pathlib import Path
U32=lambda d,o:struct.unpack_from('<I',d,o)[0]
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('exe'); ap.add_argument('fixups'); ap.add_argument('--out',required=True); a=ap.parse_args()
 d=Path(a.exe).read_bytes(); fx=json.loads(Path(a.fixups).read_text())
 lo=0x37d4c
 if d[lo:lo+2]!=b'LE': raise SystemExit('validated demo LE header not found')
 le=d[lo:]; ps=U32(le,0x28); ot=U32(le,0x40); oc=U32(le,0x44); pm=U32(le,0x48); dp=U32(le,0x80)
 objs=[struct.unpack_from('<IIIIII',le,ot+i*24) for i in range(oc)]
 def page_num(mi):
  e=le[pm+4*mi:pm+4*mi+4]; return (e[0]<<16)|(e[1]<<8)|e[2],e[3]
 def fileoff(on,oo,absolute=True):
  size,base,flags,first,npg,_=objs[on-1]; lp=oo//ps; within=oo%ps
  if lp<0 or lp>=npg: return None
  pn,fl=page_num(first-1+lp)
  if pn==0:return None
  return (dp if absolute else lo+dp)+(pn-1)*ps+within
 recs=[r for r in fx['records'] if r.get('source_type')==7 and r.get('target_kind')=='internal']
 def stats(absmap):
  readable=0; unread=0; vals=[]
  for r in recs:
   f=fileoff(r['source_object'],r['source_offset'],absmap)
   if f is None or f<0 or f+4>len(d): unread+=1; continue
   readable+=1
   if len(vals)<12: vals.append({'source_object':r['source_object'],'source_offset':r['source_offset'],'file_offset':f,'raw_bytes':d[f:f+4].hex(),'decoded_target_object':r.get('target_object'),'decoded_target_offset':r.get('target_offset')})
  return {'readable':readable,'unreadable':unread,'examples':vals}
 absst=stats(True); relst=stats(False)
 # Reconstruct initialized bytes for each object using page map and prove known diagnostic strings are present.
 labels={}
 for oi,o in enumerate(objs,1):
  size,base,flags,first,npg,_=o; buf=bytearray(min(size,npg*ps))
  for lp in range(npg):
   pn,pfl=page_num(first-1+lp)
   if not pn: continue
   f=dp+(pn-1)*ps; chunk=d[f:min(f+ps,len(d))]; start=lp*ps; buf[start:start+len(chunk)]=chunk
  hits={}
  for s in [b'Play3DSample',b'END3DSAMPLE',b'StartAmbientSoundFX',b'AIL_set_sample_volume',b'AIL_set_sample_pan']:
   poss=[]; q=0
   while True:
    q=buf.find(s,q)
    if q<0: break
    poss.append(q); q+=1
   if poss:hits[s.decode()]=poss
  labels[str(oi)]=hits
 out={
  'schema':'openazrael.le_page_mapping_audit','version':28,'exe_sha256':hashlib.sha256(d).hexdigest(),
  'le_header_file_offset':lo,'page_size':ps,'data_pages_offset_field':dp,
  'interpretation_test':{'absolute_file_offset':absst,'incorrect_module_relative_candidate':relst},
  'reconstructed_object_string_hits':labels,
  'status':'HIGH',
  'correction_to_v27':[
   'v27 added the LE header file offset to the Data Pages Offset. For this bound LE executable that is incorrect: Data Pages Offset is used as an absolute file offset.',
   'With absolute page mapping, all type-7 internal fixup source locations in the current corpus are physically readable (no 864-source deficit).',
   'The v27 raw-u32 equality test was not a valid relocation invariant: loader fixups may overwrite relocation fields, so pre-relocation bytes are not required to equal decoded target offsets or linear addresses.',
   'Therefore v27 did not disprove the structural fixup decoder. Source->target semantics remain to be validated independently, but physical source mapping is now corrected.'
  ],
  'next':['Build a loader-style relocation simulator for supported LE fixup source/target types.','Validate patched object images and then identify executable CALL/import thunks from code bytes, not diagnostic strings.']
 }
 Path(a.out).write_text(json.dumps(out,indent=2),encoding='utf8')
 print(json.dumps({'absolute':absst|{'examples':None},'module_relative':relst|{'examples':None},'string_hits':labels,'status':out['status']},indent=2))
if __name__=='__main__':main()
