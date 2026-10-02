#!/usr/bin/env python3
"""OpenAzrael Retail-RE-K001 deterministic geometry extraction runner.
Derived outputs only; original corpus remains read-only and authoritative.
"""
from __future__ import annotations
import argparse, hashlib, json, re
from pathlib import Path

EXPECTED_BIN_SIZE=511_023_744
EXPECTED_BIN_MD5='42911c0462049cee17c0bbef17b24f69'
PINNED_TOOLS={
 'azf_decode_v14.py':'23061c0ad976224a67bf2ab9861ae43deb3730a1',
 'export_xaf_glb_v8.py':'d4f361d0542fb3cba6d192faba89f26d4f7a718d',
 'legacy_colorkey.py':'1a6f83fcab01f1be5386468752688c47f75f8e86',
}

def digest(p:Path,algo='sha256'):
 h=hashlib.new(algo)
 with p.open('rb') as f:
  for b in iter(lambda:f.read(4*1024*1024),b''): h.update(b)
 return h.hexdigest()

def git_blob_sha(p:Path):
 d=p.read_bytes(); return hashlib.sha1(b'blob '+str(len(d)).encode()+b'\0'+d).hexdigest()

def die(msg): raise SystemExit('BLOCKED: '+msg)

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument('--source-root',type=Path,required=True,help='Read-only canonical retail root containing AZT.BIN/CUE and GAME/AZRAEL')
 ap.add_argument('--preextracted-root',type=Path,help='Optional verified CD extraction root containing XAF/AZF; never authority')
 ap.add_argument('--tools-root',type=Path,required=True)
 ap.add_argument('--out',type=Path,required=True)
 ap.add_argument('--attest-only',action='store_true')
 a=ap.parse_args(); src=a.source_root.resolve(); out=a.out.resolve(); tools=a.tools_root.resolve()
 binp=src/'AZT.BIN'; cue=src/'AZT.CUE'; game=src/'GAME'/'AZRAEL'; maps=game/'MAPS.DAT'
 for p in (binp,cue,maps):
  if not p.is_file(): die(f'missing canonical input: {p}')
 if binp.stat().st_size!=EXPECTED_BIN_SIZE: die(f'AZT.BIN size {binp.stat().st_size} != {EXPECTED_BIN_SIZE}')
 md5=digest(binp,'md5')
 if md5!=EXPECTED_BIN_MD5: die(f'AZT.BIN MD5 {md5} != {EXPECTED_BIN_MD5}')
 tool_att={}
 for name,blob_sha in PINNED_TOOLS.items():
  p=tools/name
  if not p.is_file(): die(f'missing pinned tool {p}')
  actual_blob=git_blob_sha(p)
  if actual_blob!=blob_sha: die(f'tool blob mismatch {name}: {actual_blob} != {blob_sha}')
  tool_att[name]={'git_blob_sha':actual_blob,'sha256':digest(p),'bytes':p.stat().st_size}
 out.mkdir(parents=True,exist_ok=True); meta=out/'metadata'; meta.mkdir(exist_ok=True)
 att={'schema':'openazrael.retail_k001.source_attestation.v1','authority':'original-retail-corpus','derived_inputs_are_not_authority':True,
      'source_root':str(src),'azt_bin':{'bytes':binp.stat().st_size,'md5':md5,'sha256':digest(binp)},
      'azt_cue':{'bytes':cue.stat().st_size,'sha256':digest(cue)},'maps_dat':{'bytes':maps.stat().st_size,'sha256':digest(maps)},
      'tools':tool_att}
 (meta/'source_attestation.json').write_text(json.dumps(att,indent=2)+'\n')
 if a.attest_only: print(json.dumps(att,indent=2)); return
 cd=(a.preextracted_root or (out/'cd_extracted')).resolve()
 if not cd.is_dir(): die('no pre-extracted CD root supplied; extraction stage must materialize canonical BIN/CUE first')
 files=[p for p in cd.rglob('*') if p.is_file()]; xaf=sorted(p for p in files if p.suffix.upper()=='.XAF'); azf=sorted(p for p in files if p.suffix.upper()=='.AZF')
 inv={'schema':'openazrael.retail_k001.cd_inventory.v1','input_role':'derived_execution_view','authority':False,'file_count':len(files),'xaf_count':len(xaf),'azf_count':len(azf),
      'xaf':[str(p.relative_to(cd)) for p in xaf],'azf':[str(p.relative_to(cd)) for p in azf]}
 (meta/'cd_inventory.json').write_text(json.dumps(inv,indent=2)+'\n')
 if not xaf: die('pre-extracted execution view contains no XAF; do not fabricate geometry')
 text=maps.read_bytes().replace(b'\x1a',b'').decode('latin1','replace'); rooms=[]; cur=None
 for raw in text.splitlines():
  line=raw.strip()
  if not line or line.startswith('//'): continue
  m=re.match(r'^ROOM\s+(\d+)\s*(.*)$',line,re.I)
  if m: cur={'room_id':int(m.group(1)),'name':m.group(2).strip(),'entries':[]}; rooms.append(cur); continue
  if re.match(r'^END\b',line,re.I): cur=None; continue
  if cur:
   m=re.match(r'^(\S+)\s+(-?\d+)\s+(-?\d+)(?:\s+(-?\d+))?',line)
   if m: cur['entries'].append({'asset':m.group(1),'x':int(m.group(2)),'y':int(m.group(3)),'target_room_id':int(m.group(4)) if m.group(4) else None})
 edges=[{'from':r['room_id'],'to':e['target_room_id'],'asset':e['asset'],'x':e['x'],'y':e['y']} for r in rooms for e in r['entries'][1:] if e['target_room_id'] is not None]
 topo={'schema':'openazrael.retail_maps_dat_topology.v1','source_sha256':digest(maps),'room_count':len(rooms),'directed_edge_count':len(edges),'rooms':rooms,'edges':edges}
 (meta/'retail_topology_maps_dat.json').write_text(json.dumps(topo,indent=2)+'\n')
 print(json.dumps({'status':'READY_FOR_DECODE','rooms':len(rooms),'edges':len(edges),'xaf':len(xaf),'azf':len(azf),'metadata':str(meta)},indent=2))
if __name__=='__main__': main()
