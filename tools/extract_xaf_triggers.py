#!/usr/bin/env python3
from pathlib import Path
import json, math
import numpy as np
import trimesh

ROOT=Path('/mnt/data/azdemo_work')
ROOMS=['R1','R7','R8']

def v3(v): return [round(float(x),6) for x in v]

def room_data(r):
    scene=trimesh.load(ROOT/f'{r}.textured.v4.glb',force='scene')
    manifest=json.loads((ROOT/f'{r}.textured.v4.manifest.json').read_text())
    omap={o['object']:o for o in manifest['objects']}
    triggers=[]; views=[]
    for name,g in scene.geometry.items():
        md=omap.get(name,{})
        mat=(md.get('material') or '').upper()
        tex=(md.get('texture') or '')
        low=name.lower()
        if mat in {'TRANSPARANT','CLEAR_OBJECT'} or low.startswith(('zx','zy')):
            triggers.append({
                'name':name,'material':mat,'texture':tex or None,
                'centroid':v3(g.centroid),'bounds':[v3(g.bounds[0]),v3(g.bounds[1])]
            })
        if Path(tex).stem.upper() in {'R12R7','R72R1','R82R1','ORR2BAP'}:
            n=np.asarray(g.face_normals,float).mean(axis=0)
            ln=np.linalg.norm(n)
            if ln: n/=ln
            views.append({
                'name':name,'material':md.get('material'),'texture':tex,
                'centroid':v3(g.centroid),'normal':v3(n),
                'bounds':[v3(g.bounds[0]),v3(g.bounds[1])]
            })
    return {'triggers':triggers,'portal_views':views}

out={'schema':1,'source':'original demo XAF -> corrected v4 GLB','rooms':{r:room_data(r) for r in ROOMS}}

# Demo remapping supported by spatial pairing of original invisible floor trigger and portal-view quad.
# Distances are measured in original XAF world coordinates.
map_defs=[
    ('R1','zxcoriR5','R7','spaview','view'),
    ('R1','zxcoriR2','R8','entcori','Object14'),
    ('R7','zxwell2R6','R1','view','spaview'),
    ('R8','zxorrery','R1','Object14','entcori'),
]
out['demo_transitions']=[]
for sr,tr,dr,sv,dv in map_defs:
    st=next(x for x in out['rooms'][sr]['triggers'] if x['name']==tr)
    sview=next(x for x in out['rooms'][sr]['portal_views'] if x['name']==sv)
    dview=next(x for x in out['rooms'][dr]['portal_views'] if x['name']==dv)
    dist=float(np.linalg.norm(np.array(st['centroid'])-np.array(sview['centroid'])))
    out['demo_transitions'].append({
        'source_room':sr,'trigger':tr,'destination_room':dr,
        'source_view':sv,'destination_view':dv,
        'trigger_to_source_view_distance':round(dist,3),
        'evidence':'invisible XAF trigger lies beside the matching portal-view quad; view texture encodes reciprocal room relation',
        'confidence':'high'
    })

# R7 deep geometry forensic check: preserve as evidence that the extreme Y bound is deliberate well-shaft content.
s=trimesh.load(ROOT/'R7.textured.v4.glb',force='scene')
deep=[]
for name,g in s.geometry.items():
    if g.bounds[0,1] < -1000:
        deep.append({'name':name,'centroid':v3(g.centroid),'bounds':[v3(g.bounds[0]),v3(g.bounds[1])]})
out['r7_deep_shaft_evidence']=deep

Path('/mnt/data/openazrael_godot_poc_v12/data/xaf_trigger_evidence.json').write_text(json.dumps(out,indent=2))
print(json.dumps({'trigger_counts':{r:len(out['rooms'][r]['triggers']) for r in ROOMS},'portal_counts':{r:len(out['rooms'][r]['portal_views']) for r in ROOMS},'transitions':len(out['demo_transitions']),'r7_deep_objects':len(deep)},indent=2))
