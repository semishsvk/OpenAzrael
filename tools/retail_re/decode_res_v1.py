#!/usr/bin/env python3
"""Decode Azrael's Tear retail .RES texture bundles."""
from __future__ import annotations
import argparse,hashlib,json,re,struct
from pathlib import Path
import numpy as np
from PIL import Image
OBJ_RE=re.compile(r'\bobject\s+"([^"]+)"\s*\{',re.I); MAT_RE=re.compile(r'\bmaterial\s+"([^"]+)"\s*\{',re.I)
def match_brace(t,o):
 d=1;i=o+1
 while d and i<len(t):
  if t[i]=='{': d+=1
  elif t[i]=='}': d-=1
  i+=1
 if d: raise ValueError(f'unmatched brace at {o}')
 return i-1
def unique_xaf_texture_refs(path):
 t=path.read_text('latin1'); iv=[]
 for m in OBJ_RE.finditer(t):
  o=t.find('{',m.start(),m.end()+1);iv.append((m.start(),match_brace(t,o)))
 refs=[]
 for m in MAT_RE.finditer(t):
  if any(a<=m.start()<=b for a,b in iv): continue
  o=t.find('{',m.start(),m.end()+1);e=match_brace(t,o);q=re.search(r'\btexture\s+"([^"]+)"',t[o+1:e],re.I)
  if q and q.group(1).lower() not in [x.lower() for x in refs]: refs.append(q.group(1))
 return refs
def records(path):
 d=path.read_bytes();p=0;out=[]
 while p<len(d):
  if p+4>len(d): raise ValueError(f'trailing bytes at {p}')
  n=struct.unpack_from('<I',d,p)[0];e=p+4+n
  if n<60 or e>len(d): raise ValueError(f'invalid record size={n} at {p}')
  out.append((p,n,d[p+4:e]));p=e
 return out
def decode_blob(b):
 w,h=struct.unpack_from('<II',b,0);pc=struct.unpack_from('<I',b,0x34)[0]
 if not 1<=pc<=256: raise ValueError(f'invalid palette_count={pc}')
 pal=np.frombuffer(b[60:60+pc*4],dtype=np.uint8).reshape(pc,4).copy();s=60+pc*4
 raw,root=struct.unpack_from('<II',b,s);tab=np.frombuffer(b[s+8:s+8+2048],dtype='<u2');stream=b[s+2056:]
 if len(tab)!=1024: raise ValueError('short node table')
 out=np.empty(raw,dtype=np.uint8);word=bits=sp=0
 for i in range(raw):
  node=root
  while node>=256:
   ti=node*2
   if ti+1>=len(tab): raise ValueError(f'node out of table: {node}')
   if bits==0:
    if sp+4>len(stream): raise EOFError(f'stream ended at output byte {i}')
    word=struct.unpack_from('<I',stream,sp)[0];sp+=4;bits=32
   node=int(tab[ti+(word&1)]);word>>=1;bits-=1
  out[i]=node
 if raw!=w*h: raise ValueError(f'raw_size {raw} != {w}*{h}')
 if int(out.max(initial=0))>=pc: raise ValueError('pixel index exceeds palette')
 return {'width':w,'height':h,'palette_count':pc,'palette':pal,'indices':out.reshape(h,w),'raw_size':raw,'root':root,'stream_bytes':len(stream),'consumed_stream_bytes':sp}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('input_res',type=Path);ap.add_argument('output_dir',type=Path);ap.add_argument('--xaf',type=Path);ap.add_argument('--manifest',type=Path);a=ap.parse_args()
 a.output_dir.mkdir(parents=True,exist_ok=True);rs=records(a.input_res);names=unique_xaf_texture_refs(a.xaf) if a.xaf else [f'record_{i:03d}.gif' for i in range(len(rs))]
 if len(names)!=len(rs): raise SystemExit(f'BLOCKED: {len(rs)} RES records != {len(names)} unique XAF texture refs')
 rep={'schema':'openazrael.retail_res_decode.v1','source':a.input_res.name,'source_sha256':hashlib.sha256(a.input_res.read_bytes()).hexdigest(),'record_count':len(rs),'mapping':'unique global XAF texture refs in first-occurrence order' if a.xaf else 'record index','mapping_evidence_state':'VERIFIED_BY_CROSS_RESOURCE_REUSE','records':[]}
 for i,((off,n,b),name) in enumerate(zip(rs,names)):
  z=decode_blob(b);rgb=z['palette'][:,:3][z['indices']];out=a.output_dir/(Path(name).stem+'.png');Image.fromarray(rgb.astype(np.uint8),'RGB').save(out)
  sem=hashlib.sha256(struct.pack('<II',z['width'],z['height'])+z['palette'].tobytes()+z['indices'].tobytes()).hexdigest()
  rep['records'].append({'index':i,'offset':off,'blob_bytes':n,'texture_ref':name,'width':z['width'],'height':z['height'],'palette_count':z['palette_count'],'raw_size':z['raw_size'],'root':z['root'],'stream_bytes':z['stream_bytes'],'consumed_stream_bytes':z['consumed_stream_bytes'],'png':out.name,'semantic_sha256':sem})
 m=a.manifest or a.output_dir/'manifest.json';m.write_text(json.dumps(rep,indent=2)+'\n');print(json.dumps({'source':rep['source'],'records':len(rs),'decoded':len(rep['records']),'manifest':str(m)},indent=2))
if __name__=='__main__': main()
