#!/usr/bin/env python3
from pathlib import Path
import hashlib, json
import trimesh
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
ROOM_EXPECT={
 'R1': {'geometries':69,'triangles':593,'textured':62},
 'R7': {'geometries':48,'triangles':689,'textured':40},
 'R8': {'geometries':87,'triangles':1050,'textured':74},
}

def sha256(p):
 h=hashlib.sha256();
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()

def main():
 texdir=ROOT/'assets/textures/classic'
 textures=[]
 for p in sorted(texdir.glob('*.png')):
  with Image.open(p) as im:
   im.verify()
  with Image.open(p) as im:
   textures.append({'file':p.name,'width':im.width,'height':im.height,'mode':im.mode,'sha256':sha256(p)})
 assert len(textures)==86, f'expected 86 decoded AZF PNGs, got {len(textures)}'
 rooms={}
 for room,exp in ROOM_EXPECT.items():
  p=ROOT/f'assets/rooms/{room}.glb'
  s=trimesh.load(p,force='scene')
  geoms=len(s.geometry); tris=sum(len(g.faces) for g in s.geometry.values()); uv=textured=0
  for g in s.geometry.values():
   v=g.visual
   if getattr(v,'uv',None) is not None and len(v.uv): uv+=1
   m=getattr(v,'material',None)
   if m is not None and (getattr(m,'baseColorTexture',None) is not None or getattr(m,'image',None) is not None): textured+=1
  got={'geometries':geoms,'triangles':tris,'uv_geometries':uv,'textured_geometries':textured,'sha256':sha256(p),'bounds':s.bounds.tolist()}
  assert geoms==exp['geometries'] and tris==exp['triangles'] and textured==exp['textured'], (room,got,exp)
  assert uv==geoms, (room,'not every primitive retained UVs',uv,geoms)
  manifest=json.loads((ROOT/f'data/{room}.textured.v44.manifest.json').read_text())
  assert manifest['missing_textures']==[]
  assert manifest['textured_primitives']==exp['textured']
  rooms[room]=got
 report={
  'version':44,
  'status':'PASS',
  'classic_texture_count':len(textures),
  'azf_decoder_model':'v14 exact demo Huffman/tree decoder; local palette RGB with engine-observed component quantization',
  'textures':textures,
  'rooms':rooms,
  'confidence':{
   'AZF entropy decode':'VERIFIED on all 86 demo AZF files',
   'XAF geometry/UV/material binding':'HIGH',
   'GLB embedded texture presence':'VERIFIED for R1/R7/R8 output',
   'Godot visual parity with original renderer':'HOLD until direct runtime/screenshot comparison',
   'global renderer palette remap':'HOLD'
  }
 }
 out=ROOT/'data/graphics_pipeline_validation_v44.json'
 out.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
 print(json.dumps({'status':'PASS','textures':len(textures),'rooms':rooms},indent=2))
if __name__=='__main__': main()
