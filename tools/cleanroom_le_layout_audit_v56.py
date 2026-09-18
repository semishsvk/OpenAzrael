#!/usr/bin/env python3
import argparse,struct,json,hashlib
from pathlib import Path
EXPECTED='381e4f5c61e4bb8c27f06b1944e6673bbebc39ca219cc08fb9f948da2ca37c00'
U32=lambda d,o:struct.unpack_from('<I',d,o)[0]
I16=lambda d,o:struct.unpack_from('<h',d,o)[0]
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('exe'); ap.add_argument('--out',required=True); a=ap.parse_args()
 raw=Path(a.exe).read_bytes(); sha=hashlib.sha256(raw).hexdigest(); lo=0x37d4c
 if raw[lo:lo+2]!=b'LE' or sha!=EXPECTED: raise SystemExit('unexpected demo LE image')
 le=raw[lo:]; n=U32(le,0x14); ps=U32(le,0x28); ot=U32(le,0x40); oc=U32(le,0x44); fpt=U32(le,0x68); frt=U32(le,0x6c); dp=U32(le,0x80)
 objs=[]
 for i in range(oc):
  size,base,flags,first,npages,res=struct.unpack_from('<IIIIII',le,ot+i*24); objs.append((size,base,flags,first,npages))
 # Clean-room parser from IBM LX/LE record grammar. No v27 JSON is consumed.
 pageoffs=[U32(le,fpt+4*i) for i in range(n+1)]; recs=[]; errs=[]
 for pg in range(n):
  p=frt+pageoffs[pg]; end=frt+pageoffs[pg+1]
  while p<end:
   start=p
   try:
    src=le[p]; flags=le[p+1]; p+=2; islist=bool(src&0x20)
    if islist: count=le[p]; p+=1; srcs=[]
    else: count=1; srcs=[I16(le,p)]; p+=2
    tk=flags&3; ord16=bool(flags&0x40); off32=bool(flags&0x10); additive=bool(flags&0x04); add32=bool(flags&0x20)
    ordsz=2 if ord16 else 1; target={'kind':tk}
    if tk==0:
     obj=int.from_bytes(le[p:p+ordsz],'little'); p+=ordsz; target['object']=obj
     if (src&0x0f)!=2:
      sz=4 if off32 else 2; target['offset']=int.from_bytes(le[p:p+sz],'little'); p+=sz
    elif tk==1:
     p+=ordsz; sz=1 if flags&0x80 else (4 if off32 else 2); p+=sz
    elif tk==2:
     p+=ordsz; p+=4 if off32 else 2
    else:
     p+=ordsz
    if additive: p+=4 if add32 else 2
    if islist:
     srcs=[I16(le,p+2*i) for i in range(count)]; p+=2*count
    for s in srcs: recs.append({'page':pg+1,'within':s,'src_type':src&0xf,'flags':flags,'target':target.copy(),'record_le_offset':start})
   except Exception as e:
    errs.append({'page':pg+1,'offset':start,'error':repr(e)}); break
 # Build object1 with module-relative Data Pages Offset (relative to LE header), as the coherent code image requires.
 size=objs[0][0]; o1=bytes(le[dp:dp+size])
 anchors={0xcf4d:'94190000',0xcf7e:'5e610000',0xd005:'54190000',0xd00b:'5c190000',0xd01e:'64190000',0xd05b:'54190000',0xd061:'5c190000',0xd074:'64190000'}
 anchor_bytes={hex(k):o1[k:k+4].hex() for k in anchors}
 exact=[]
 for aoff in anchors:
  pg=aoff//ps+1; within=aoff%ps
  exact += [r for r in recs if r['page']==pg and r['within']==within]
 # Strong v28 falsifier: raw[dp] lies in loader/fixup area, while raw[lo+dp] is the coherent first code page.
 module_rel_head=raw[lo+dp:lo+dp+16].hex(); absolute_head=raw[dp:dp+16].hex()
 checks={
  'cleanroom_record_count_28547':len(recs)==28547,
  'cleanroom_no_parse_errors':not errs,
  'all_records_source_type_7':all(r['src_type']==7 for r in recs),
  'all_anchor_bytes_match':all(anchor_bytes[hex(k)]==v for k,v in anchors.items()),
  'zero_exact_anchor_fixups':len(exact)==0,
  'module_relative_dp_starts_coherent_object1':module_rel_head=='008d8424c800000031d2e8414902008d',
  'absolute_dp_is_not_object1':absolute_head!=module_rel_head,
 }
 if not all(checks.values()): raise SystemExit(checks)
 out={'schema':'openazrael.cleanroom_le_layout_audit','version':56,'status':'PASS','exe_sha256':sha,'invariants':checks,
  'cleanroom':{'records':len(recs),'errors':errs,'source_type_histogram':{str(i):sum(r['src_type']==i for r in recs) for i in sorted(set(r['src_type'] for r in recs))}},
  'data_pages_offset':{'field':hex(dp),'le_header_file_offset':hex(lo),'correct_bound_file_first_page':hex(lo+dp),'correct_first16':module_rel_head,'v28_absolute_candidate':hex(dp),'v28_candidate_first16':absolute_head,
   'decision':'V28_ABSOLUTE_FILE_OFFSET_CLAIM_SUPERSEDED; for this bound DOS/4GW LE image the field is module-relative to the LE header when locating embedded data pages.'},
  'anchor_test':{'anchors':{hex(k):{'bytes':anchor_bytes[hex(k)],'page':k//ps+1,'within':hex(k%ps)} for k in anchors},'exact_cleanroom_matches':len(exact)},
  'findings':['A clean-room IBM-grammar parser independently reproduces 28,547 structural fixup records; the v27 record grammar itself is not the source of the operand mismatch.','The v28 claim that Data Pages Offset is an absolute bound-file offset is falsified by the executable bytes. The coherent object-1 code begins at LE_header + Data_Pages_Offset.','Even with the clean-room parser, none of the eight independently decoded 0xCDE1 disp32 anchors is an exact fixup source. Therefore source-to-instruction binding remains HOLD and must not be repaired heuristically.'],
  'supersedes':['v28: Data Pages Offset is absolute file offset','Any later evidence that relies on v28 absolute physical source-file mapping'],
  'retained':['v54/v55 quarantine of operand-level legacy fixup semantics','instruction-level 0xCDE1 symbolic math','v50 ambient loop correction','v48/v49 playback-rate findings'],
  'confidence':{'cleanroom_fixup_record_grammar':'HIGH','bound_LE_data_page_location':'HIGH','v28_absolute_mapping_invalid':'HIGH','fixup_source_to_x86_operand':'HOLD','numeric_3d_constants':'HOLD'},
  'next':['Investigate why the structurally valid fixup pages do not correspond to the embedded bound object image operand sites (binding/unbinding transformation or loader preprocessing).','Do not use v28 physical file offsets for forensic source binding.','Recover attenuation/pan constants by an independent initialized-data or loader-emulation path before enabling exact Classic 3D math.']}
 Path(a.out).write_text(json.dumps(out,indent=2),encoding='utf8'); print(json.dumps({'status':'PASS','checks':len(checks),'records':len(recs),'anchor_matches':len(exact),'v28':'SUPERSEDED'},indent=2))
if __name__=='__main__': main()
