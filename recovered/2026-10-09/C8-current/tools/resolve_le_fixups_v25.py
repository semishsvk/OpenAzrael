#!/usr/bin/env python3
"""Resolve internal Watcom LE fixups into source/target object coordinates.
Conservative forensic tool: it does not claim function identities from strings.
"""
from pathlib import Path
import argparse,struct,json,hashlib
U16=lambda d,o:struct.unpack_from('<H',d,o)[0]
U32=lambda d,o:struct.unpack_from('<I',d,o)[0]
I16=lambda d,o:struct.unpack_from('<h',d,o)[0]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('exe');ap.add_argument('--out',required=True);a=ap.parse_args()
 d=Path(a.exe).read_bytes(); leoff=0x37D4C
 if leoff<0: raise SystemExit('LE not found')
 le=d[leoff:]; n=U32(le,0x14); ps=U32(le,0x28); ot=U32(le,0x40); oc=U32(le,0x44); fpt=U32(le,0x68); frt=U32(le,0x6c)
 objs=[]
 for i in range(oc):
  size,base,flags,first,npages,_=struct.unpack_from('<IIIIII',le,ot+i*24)
  objs.append(dict(number=i+1,size=size,base=base,first_page=first,page_count=npages))
 pages=[U32(le,fpt+4*i) for i in range(n+1)]
 def src_obj(pg0):
  p=pg0+1
  for o in objs:
   if o['first_page']<=p<o['first_page']+o['page_count']:
    return o,(p-o['first_page'])*ps
  return None,None
 recs=[]; errors=[]
 for pg in range(n):
  p=frt+pages[pg]; end=frt+pages[pg+1]
  while p<end:
   rs=p
   try:
    typ,fl=le[p],le[p+1];p+=2; islist=bool(typ&0x20)
    if islist: ns=le[p];p+=1; srcs=[]
    else: srcs=[I16(le,p)];p+=2; ns=0
    ordsz=2 if fl&0x40 else 1; tk=fl&3; tgt=None
    if tk==0:
     obj=U16(le,p) if ordsz==2 else le[p];p+=ordsz; off=None
     if (typ&0xf)!=2:
      off=U32(le,p) if fl&0x10 else U16(le,p);p+=4 if fl&0x10 else 2
     if fl&0x04:p+=4 if fl&0x20 else 2
     tgt=('internal',obj,off)
    elif tk==1:
     p+=ordsz
     if fl&0x80:p+=1
     else:p+=4 if fl&0x10 else 2
     if fl&0x04:p+=4 if fl&0x20 else 2
     tgt=('import_ordinal',None,None)
    elif tk==2:
     p+=ordsz;p+=4 if fl&0x10 else 2
     if fl&0x04:p+=4 if fl&0x20 else 2
     tgt=('import_name',None,None)
    else:
     p+=ordsz
     if fl&0x04:p+=4 if fl&0x20 else 2
     tgt=('entry',None,None)
    if islist: srcs=[I16(le,p+2*i) for i in range(ns)];p+=2*ns
    so,pbase=src_obj(pg)
    for s in srcs:
     r={'page':pg+1,'source_type':typ&0xf,'source_object':so['number'] if so else None,'source_offset':pbase+s if so else None,'source_linear':so['base']+pbase+s if so else None,'target_kind':tgt[0]}
     if tgt[0]=='internal':
      r['target_object']=tgt[1];r['target_offset']=tgt[2]
      if tgt[2] is not None and 1<=tgt[1]<=len(objs):r['target_linear']=objs[tgt[1]-1]['base']+tgt[2]
     recs.append(r)
   except Exception as e: errors.append({'page':pg+1,'record':hex(rs),'error':repr(e)});break
 # High-value audit: diagnostic labels used in prior Play3D work.
 dp=U32(le,0x80); labels=[]
 for o in objs:
  st=leoff+dp+(o['first_page']-1)*ps; blob=d[st:st+o['size']]
  for nm in [b'Play3DSample',b'END3DSAMPLE',b'StartAmbientSoundFX']:
   q=0
   while True:
    q=blob.find(nm,q)
    if q<0:break
    x=[r for r in recs if r['target_kind']=='internal' and r.get('target_object')==o['number'] and r.get('target_offset')==q]
    labels.append({'label':nm.decode(),'object':o['number'],'offset':q,'linear':o['base']+q,'resolved_fixup_xrefs':len(x),'xref_sources':[{'object':z['source_object'],'offset':z['source_offset']} for z in x[:32]]});q+=1
 out={'schema':'openazrael.le_fixups','version':25,'sha256':hashlib.sha256(d).hexdigest(),'records':len(recs),'errors':errors,'internal_records':sum(r['target_kind']=='internal' for r in recs),'source_type_histogram':{},'target_kind_histogram':{},'play3d_label_audit':labels,'interpretation':['LE page-table + record-table source coordinates are now emitted as object-relative and linear coordinates.','Internal targets are resolved to target object + offset + relocation-base linear address.','Play3DSample/StartAmbientSoundFX labels still have zero exact internal-fixup xrefs; they remain diagnostic evidence, not function addresses.']}
 for r in recs: out['source_type_histogram'][str(r['source_type'])]=out['source_type_histogram'].get(str(r['source_type']),0)+1;out['target_kind_histogram'][r['target_kind']]=out['target_kind_histogram'].get(r['target_kind'],0)+1
 Path(a.out).write_text(json.dumps(out,indent=2),encoding='utf8');print(json.dumps({k:out[k] for k in ['records','internal_records','source_type_histogram','target_kind_histogram','play3d_label_audit']},indent=2))
if __name__=='__main__':main()
