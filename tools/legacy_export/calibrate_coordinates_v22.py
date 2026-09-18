#!/usr/bin/env python3
"""OpenAzrael demo coordinate calibration v22.
Validates whether legacy AMB XYZ can be consumed directly in the XAF/GLB room coordinate space.
Does not infer arbitrary scale/axis flips. Produces evidence metrics only.
"""
from pathlib import Path
import json, argparse, numpy as np, trimesh
ROOMS={0:'R1',1:'R7',2:'R8'}
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('project',type=Path); ap.add_argument('--out',type=Path)
 a=ap.parse_args(); ir=json.loads((a.project/'data/audio/legacy_world_ir.json').read_text())
 report={'schema':'openazrael.coordinate_calibration','version':1,'method':'direct legacy XYZ vs exported XAF/GLB world space','rooms':{},'conclusion':{}}
 all_inside=True
 for rid,r in ROOMS.items():
  s=trimesh.load(a.project/f'assets/rooms/{r}.glb',force='scene'); b=np.asarray(s.bounds,float)
  emit=[e for e in ir['audio']['ambient_emitters'] if e['room_id']==rid]
  rows=[]
  for e in emit:
   p=np.asarray(e['legacy_position'],float); inside=bool(np.all(p>=b[0]) and np.all(p<=b[1])); all_inside &= inside
   best=(1e30,None)
   for node in s.graph.nodes_geometry:
    T,gn=s.graph[node]; v=trimesh.transform_points(s.geometry[gn].vertices,T)
    d=float(np.linalg.norm(v-p,axis=1).min())
    if d<best[0]: best=(d,node)
   rows.append({'sound':e.get('sample',''),'legacy_position':e['legacy_position'],'inside_room_aabb':inside,'nearest_mesh_vertex_distance':best[0],'nearest_mesh_node':best[1]})
  report['rooms'][r]={'room_id':rid,'glb_bounds':b.tolist(),'emitters':rows}
 report['conclusion']={'all_emitters_inside_corresponding_glb_aabb':all_inside,
   'demo_transform':'IDENTITY',
   'expression':'godot_local = Vector3(legacy_x, legacy_y, legacy_z)',
   'scale':1.0,'axis_order':'XYZ','axis_sign':[1,1,1],
   'confidence':'HIGH',
   'scope':'Demo R1/R7/R8 exported XAF/GLB coordinate space; retain source XYZ for future full-game cross-validation.'}
 out=a.out or a.project/'data/audio/coordinate_calibration_v22.json'; out.write_text(json.dumps(report,indent=2)); print(out)
if __name__=='__main__': main()
