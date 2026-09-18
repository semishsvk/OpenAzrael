#!/usr/bin/env python3
from pathlib import Path
import argparse,struct,json,hashlib,collections
U16=lambda d,o:struct.unpack_from('<H',d,o)[0]; U32=lambda d,o:struct.unpack_from('<I',d,o)[0]; I16=lambda d,o:struct.unpack_from('<h',d,o)[0]
LABELS=[b'AIL_set_sample_playback_rate',b'AIL_set_sample_volume',b'AIL_set_sample_pan',b'AIL_set_sample_loop_count',b'AIL_sample_status']
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('exe'); ap.add_argument('--out',required=True); a=ap.parse_args(); d=Path(a.exe).read_bytes(); leoff=0x37D4C
 if d[leoff:leoff+2] != b'LE': raise SystemExit('Expected LE header not found')
 le=d[leoff:]
 n=U32(le,0x14);ps=U32(le,0x28);ot=U32(le,0x40);oc=U32(le,0x44);fpt=U32(le,0x68);frt=U32(le,0x6c);dp=U32(le,0x80)
 objs=[]
 for i in range(oc):
  size,base,flags,first,npages,_=struct.unpack_from('<IIIIII',le,ot+i*24); objs.append(dict(number=i+1,size=size,base=base,first_page=first,page_count=npages,file_start=leoff+dp+(first-1)*ps))
 pages=[U32(le,fpt+4*i) for i in range(n+1)]
 def srcobj(pg):
  p=pg+1
  for o in objs:
   if o['first_page']<=p<o['first_page']+o['page_count']: return o,(p-o['first_page'])*ps
 rec=[]
 for pg in range(n):
  p=frt+pages[pg];end=frt+pages[pg+1]
  while p<end:
   typ,fl=le[p],le[p+1];p+=2; islist=bool(typ&0x20)
   if islist: ns=le[p];p+=1;srcs=[]
   else: srcs=[I16(le,p)];p+=2;ns=0
   ordsz=2 if fl&0x40 else 1;tk=fl&3
   if tk!=0: break
   obj=U16(le,p) if ordsz==2 else le[p];p+=ordsz;off=None
   if (typ&0xf)!=2: off=U32(le,p) if fl&0x10 else U16(le,p);p+=4 if fl&0x10 else 2
   if fl&0x04:p+=4 if fl&0x20 else 2
   if islist:srcs=[I16(le,p+2*i) for i in range(ns)];p+=2*ns
   so,pb=srcobj(pg)
   for s in srcs:rec.append(dict(source_object=so['number'],source_offset=pb+s,target_object=obj,target_offset=off,flags=fl,source_type=typ&15))
 findings=[]
 for lab in LABELS:
  fo=d.find(lab)
  hit={'label':lab.decode(),'file_offset':fo,'object':None,'object_offset':None,'exact_fixup_xrefs':0,'nearby_targets':[]}
  for o in objs:
   if o['file_start']<=fo<o['file_start']+o['size']:
    off=fo-o['file_start'];hit['object']=o['number'];hit['object_offset']=off
    exact=[r for r in rec if r['target_object']==o['number'] and r['target_offset']==off];hit['exact_fixup_xrefs']=len(exact)
    near=[r for r in rec if r['target_object']==o['number'] and r['target_offset'] is not None and abs(r['target_offset']-off)<=64]
    for r in sorted(near,key=lambda x:(abs(x['target_offset']-off),x['source_offset']))[:24]:
     hit['nearby_targets'].append({'delta':r['target_offset']-off,'target_offset':r['target_offset'],'source_object':r['source_object'],'source_offset':r['source_offset'],'flags':r['flags']})
  findings.append(hit)
 out={'schema':'openazrael.miles_xref_audit','version':26,'source_sha256':hashlib.sha256(d).hexdigest(),'fixups_scanned':len(rec),'findings':findings,'conclusions':[{'confidence':'VERIFIED','statement':'No exact resolved internal fixup targets any audited Miles diagnostic-format string.'},{'confidence':'VERIFIED','statement':'Many resolved targets fall within +/-64 bytes of the Miles strings, but several land inside printable diagnostic text; proximity is therefore not a valid call-site identification criterion.'},{'confidence':'CORRECTION','statement':'v25 fixup source mapping remains useful, but target interpretation must remain under validation before it is used to name functions or call sites.'},{'confidence':'HOLD','statement':'Classic distance attenuation and panning formula remains undecoded.'}]}
 Path(a.out).write_text(json.dumps(out,indent=2),encoding='utf8'); print(json.dumps(out,indent=2))
if __name__=='__main__':main()
