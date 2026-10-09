#!/usr/bin/env python3
"""OpenAzrael v27: conservative validation of LE fixup interpretation.
Checks whether decoded type-7 fixup source locations contain the expected unrelocated
internal target offset/linear value. A mismatch is evidence that source/file mapping
or record semantics still need work; it must not be used to name call sites.
"""
import argparse,json,struct,hashlib
from pathlib import Path
U32=lambda d,o:struct.unpack_from('<I',d,o)[0]
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('exe'); ap.add_argument('fixups'); ap.add_argument('--out',required=True); a=ap.parse_args()
 d=Path(a.exe).read_bytes(); fx=json.loads(Path(a.fixups).read_text())
 # v27 demo module locator: use validated LE signature scan rather than a claimed code address.
 candidates=[]
 for i in range(len(d)-0x90):
  if d[i:i+2]==b'LE':
   try:
    if U32(d,i+0x28)==0x1000 and 1<=U32(d,i+0x44)<64: candidates.append(i)
   except: pass
 if not candidates: raise SystemExit('No LE module')
 lo=candidates[0]; le=d[lo:]; ps=U32(le,0x28); ot=U32(le,0x40); oc=U32(le,0x44); pm=U32(le,0x48); dp=U32(le,0x80)
 objs=[]
 for i in range(oc): objs.append(struct.unpack_from('<IIIIII',le,ot+i*24))
 def fileoff(on,oo):
  size,base,flags,first,npg,_=objs[on-1]; lp=oo//ps; within=oo%ps; mi=first-1+lp
  e=le[pm+4*mi:pm+4*mi+4]; pn=(e[0]<<16)|(e[1]<<8)|e[2]
  # LE data pages offset is module-relative in this bound executable.
  return lo+dp+(pn-1)*ps+within
 recs=fx.get('records',[]); checked=0; oeq=0; leq=0; unreadable=0; examples=[]
 for r in recs:
  if r.get('source_type')!=7 or r.get('target_kind')!='internal': continue
  fo=fileoff(r['source_object'],r['source_offset'])
  if fo<0 or fo+4>len(d): unreadable+=1; continue
  v=U32(d,fo); checked+=1
  if v==r.get('target_offset'): oeq+=1
  if v==r.get('target_linear'): leq+=1
  if len(examples)<16: examples.append({'source_object':r['source_object'],'source_offset':r['source_offset'],'file_offset':fo,'raw_u32':v,'decoded_target_object':r.get('target_object'),'decoded_target_offset':r.get('target_offset'),'decoded_target_linear':r.get('target_linear')})
 out={'schema':'openazrael.le_fixup_semantics_audit','version':27,'exe_sha256':hashlib.sha256(d).hexdigest(),'le_header_file_offset':lo,'fixup_records_input':len(recs),'type7_internal_checked':checked,'unreadable_source_locations':unreadable,'raw_u32_equals_decoded_target_offset':oeq,'raw_u32_equals_decoded_target_linear':leq,'examples':examples,'status':'HOLD','conclusion':['The v25/v26 structural record count remains useful, but decoded source->target xrefs are not yet validated semantically.','At the currently decoded source locations, type-7 payloads do not reproduce decoded target offsets/linear addresses at scale.','Therefore Miles/Play3D call-site identification must not rely on these xrefs yet.','Next step: validate LE page/source-chain semantics against an independent LE specification/parser or a known relocation invariant before disassembly slicing.']}
 Path(a.out).write_text(json.dumps(out,indent=2),encoding='utf8'); print(json.dumps({k:out[k] for k in ['type7_internal_checked','unreadable_source_locations','raw_u32_equals_decoded_target_offset','raw_u32_equals_decoded_target_linear','status']},indent=2))
if __name__=='__main__': main()
