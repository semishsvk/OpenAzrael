from pathlib import Path
import re, sys, json, hashlib
from collections import defaultdict
import numpy as np
import trimesh
from PIL import Image
from legacy_colorkey import image_alpha_mode

OBJ_RE = re.compile(r'\bobject\s+"([^"]+)"\s*\{', re.I)
MAT_RE = re.compile(r'\bmaterial\s+"([^"]+)"\s*\{', re.I)


def match_brace(text, open_pos):
    d=1; i=open_pos+1
    while d and i < len(text):
        c=text[i]
        if c=='{': d+=1
        elif c=='}': d-=1
        i+=1
    if d: raise ValueError(f'unmatched brace at {open_pos}')
    return i-1


def all_object_nodes(text):
    """Return object nodes with exact nesting inferred from brace intervals."""
    raw=[]
    for m in OBJ_RE.finditer(text):
        op=text.find('{',m.start(),m.end()+1)
        cl=match_brace(text,op)
        raw.append({'name':m.group(1),'header_start':m.start(),'open':op,'close':cl})
    raw.sort(key=lambda x:x['header_start'])
    stack=[]
    for n in raw:
        while stack and n['header_start'] > stack[-1]['close']:
            stack.pop()
        n['parent_index'] = raw.index(stack[-1]) if stack else None
        # avoid O(n) lookup after this pass by storing parent object directly for now
        n['_parent'] = stack[-1] if stack else None
        stack.append(n)
    idx={id(n):i for i,n in enumerate(raw)}
    for n in raw:
        n['parent_index']=idx[id(n['_parent'])] if n['_parent'] is not None else None
        del n['_parent']
    return raw


def direct_section(body, name):
    pat=re.compile(r'\b'+re.escape(name)+r'\s*\{',re.I)
    depth=0; i=0
    while i<len(body):
        if depth==0:
            m=pat.match(body,i)
            if m:
                op=body.find('{',m.start(),m.end()+1)
                cl=match_brace(body,op)
                return body[op+1:cl]
        c=body[i]
        if c=='{': depth+=1
        elif c=='}': depth-=1
        i+=1
    return None


def nums(s):
    return [float(x) for x in re.findall(r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?', s)]


def material_table(t):
    # Global material blocks occur before object hierarchy in these demo XAF files.
    out={}
    # Parse every material header but exclude those nested in object intervals by brace depth.
    objs=all_object_nodes(t)
    intervals=[(o['header_start'],o['close']) for o in objs]
    for m in MAT_RE.finditer(t):
        pos=m.start()
        if any(a <= pos <= b for a,b in intervals):
            continue
        op=t.find('{',m.start(),m.end()+1); cl=match_brace(t,op); b=t[op+1:cl]
        mt=re.search(r'\btexture\s+"([^"]+)"',b,re.I)
        mc=direct_section(b,'colour')
        vals=nums(mc) if mc else []
        out[m.group(1)]={'texture':mt.group(1) if mt else None,'colour':vals[:4] if len(vals)>=4 else None}
    return out


def texture_index(texture_dir):
    return {p.stem.upper():p for p in Path(texture_dir).glob('*.png')}

def resolve_texture(tex_name,idx):
    return idx.get(Path(tex_name).stem.upper()) if tex_name else None


UV_EXPORT_CORRECTION = "TRIMESH_PRE_FLIP_V_PRESERVE_XAF_GLTF"

def corrected_uvs(tex_name, uvs):
    """Preserve the original XAF UVs in the exported raw glTF/GLB.

    The recovered XAF corpus already uses the same semantic V direction as
    glTF: V=0 is the top of an image.  Trimesh's TextureVisuals uses the
    opposite internal image convention and flips V again while writing glTF.
    Therefore we pre-flip V once *for the exporter adapter only*.  The raw GLB
    TEXCOORD_0 values then match the original XAF authored UVs exactly.

    This is deliberately global and content-neutral.  Do not add per-texture
    orientation hacks here; source-authored back-face/state geometry is handled
    by the object transform/state logic, not by changing its UV data.
    """
    corrected=np.array(uvs,float,copy=True)
    if len(corrected):
        corrected[:,1]=1.0-corrected[:,1]
    return corrected,UV_EXPORT_CORRECTION

def face_records(fs):
    out=[]
    for line in fs.splitlines():
        z=[int(x) for x in re.findall(r'-?\d+',line)]
        if not z or z[0] < 3: continue
        count,p=z[0],z[1:]
        if len(p) < 2*count: continue
        out.append([(p[2*i],p[2*i+1]) for i in range(count)])
    return out


def face_material_names(meshb, poly_count):
    fm=direct_section(meshb,'face_materials')
    if fm is not None:
        names=re.findall(r'"([^"]+)"',fm)
        if len(names)==poly_count:
            return names,'face_materials'
    mm=re.search(r'\bmaterial\s+"([^"]+)"',meshb,re.I)
    mn=mm.group(1) if mm else 'DEFAULT'
    return [mn]*poly_count,'single_material'


def parse(src,texture_dir):
    src=Path(src); t=src.read_text('latin1')
    mats=material_table(t); tex_idx=texture_index(texture_dir)
    scene=trimesh.Scene(); missing=set(); resolved=set(); material_cache={}; material_alpha={}
    nodes=all_object_nodes(t)
    # Unique names are expected in demo rooms; disambiguate defensively.
    used=defaultdict(int)
    for n in nodes:
        base=n['name']; used[base]+=1
        n['scene_name']=base if used[base]==1 else f'{base}__dup{used[base]}'
    for i,n in enumerate(nodes):
        n['parent_scene_name']=nodes[n['parent_index']]['scene_name'] if n['parent_index'] is not None else scene.graph.base_frame

    def get_material(mn):
        if mn in material_cache: return material_cache[mn]
        md=mats.get(mn,{}); tex_name=md.get('texture'); tex_path=resolve_texture(tex_name,tex_idx)
        if tex_name and tex_path is None: missing.add(tex_name)
        if tex_path is not None:
            resolved.add(tex_path.name)
            with Image.open(tex_path) as source_image:
                source_image.load()
                image=source_image.copy()
            alpha_mode=image_alpha_mode(image, tex_path)
            material_alpha[mn]=alpha_mode
            if alpha_mode == 'MASK':
                mat=trimesh.visual.material.PBRMaterial(
                    baseColorTexture=image.convert('RGBA'),
                    metallicFactor=0.0,
                    roughnessFactor=1.0,
                    alphaMode='MASK',
                    alphaCutoff=0.5,
                    name=mn,
                )
            else:
                mat=trimesh.visual.material.SimpleMaterial(image=image.convert('RGB'),name=mn)
        else:
            col=md.get('colour'); rgba=[max(0,min(255,round(x*255))) for x in col[:4]] if col else [180,180,180,255]
            if col and len(rgba) >= 4 and rgba[3] < 255:
                material_alpha[mn]='BLEND'
                mat=trimesh.visual.material.PBRMaterial(
                    baseColorFactor=rgba,
                    metallicFactor=0.0,
                    roughnessFactor=1.0,
                    alphaMode='BLEND',
                    name=mn,
                )
            else:
                material_alpha[mn]='OPAQUE'
                mat=trimesh.visual.material.SimpleMaterial(diffuse=rgba,name=mn)
        material_cache[mn]=mat; return mat

    object_stats=[]; primitive_stats=[]
    for i,nod in enumerate(nodes):
        body=t[nod['open']+1:nod['close']]
        ms=direct_section(body,'matrix'); M=np.eye(4)
        if ms and len(nums(ms))>=16: M=np.array(nums(ms)[:16]).reshape(4,4)
        local_transform=M.T
        name=nod['scene_name']; parent=nod['parent_scene_name']
        # Always create an object node so hierarchy and pivots survive even for objects with no mesh.
        scene.graph.update(frame_to=name,frame_from=parent,matrix=local_transform)

        meshb=direct_section(body,'mesh')
        objrec={'object':nod['name'],'scene_node':name,'parent':None if nod['parent_index'] is None else nodes[nod['parent_index']]['name'],
                'depth':0,'matrix':M.tolist(),'pivot_local':M[3,:3].tolist(),'has_mesh':False,
                'primitive_count':0,'corner_vertices':0,'triangles':0,'bad_uv_corners':0,'bad_normal_corners':0,'materials':[]}
        p=nod['parent_index']
        while p is not None:
            objrec['depth']+=1; p=nodes[p]['parent_index']
        if not meshb:
            object_stats.append(objrec); continue
        vs,ns,us,fs=[direct_section(meshb,x) for x in ['vertices','normals','texture_coordinates','faces']]
        if not vs or not fs:
            object_stats.append(objrec); continue
        v=np.array(nums(vs),float).reshape(-1,3)
        nrm=np.array(nums(ns),float).reshape(-1,3) if ns else np.zeros((0,3))
        uv=np.array(nums(us),float).reshape(-1,2) if us else np.zeros((0,2))
        polys=face_records(fs)
        if not polys:
            object_stats.append(objrec); continue
        p_mats,mat_mode=face_material_names(meshb,len(polys)); groups=defaultdict(list)
        for poly,mn in zip(polys,p_mats): groups[mn].append(poly)
        objrec.update({'has_mesh':True,'vertex_count_source':len(v),'uv_count_source':len(uv),'normal_count_source':len(nrm),
                       'polygon_count_source':len(polys),'material_mode':mat_mode,'materials':list(groups.keys()),
                       'local_bounds':[v.min(axis=0).tolist(),v.max(axis=0).tolist()]})
        for gi,(mn,gpolys) in enumerate(groups.items()):
            ov=[]; on=[]; ouv=[]; of=[]; bad_uv=bad_normal=0
            for poly in gpolys:
                corners=[]
                for vi,ni in poly:
                    if not (0<=vi<len(v)): continue
                    corners.append(len(ov)); ov.append(v[vi])
                    if len(uv) and vi<len(uv): ouv.append(uv[vi])
                    else: ouv.append([0.,0.]); bad_uv += 1 if len(uv) else 0
                    if len(nrm) and 0<=ni<len(nrm): on.append(nrm[ni])
                    else: on.append([0.,1.,0.]); bad_normal += 1 if len(nrm) else 0
                if len(corners)!=len(poly): continue
                for k in range(1,len(poly)-1): of.append([corners[0],corners[k],corners[k+1]])
            if not of: continue
            tex=mats.get(mn,{}).get('texture')
            material=get_material(mn)
            source_uv=np.asarray(ouv,dtype="<f4")
            corrected_uv,uv_correction=corrected_uvs(tex,source_uv)
            # Preserve adapter precision until trimesh applies its matching V flip
            # and performs the final float32 glTF cast. Quantizing the pre-flipped
            # values here makes the round-trip non-bit-exact for authored XAF UVs.
            export_uv=np.asarray(corrected_uv,dtype="<f8")
            source_uv_sha256=hashlib.sha256(source_uv.tobytes()).hexdigest()
            export_input_uv_sha256=hashlib.sha256(export_uv.tobytes()).hexdigest()
            visual=trimesh.visual.TextureVisuals(uv=export_uv,material=material)
            mesh=trimesh.Trimesh(vertices=np.array(ov),faces=np.array(of),vertex_normals=np.array(on),visual=visual,process=False)
            mesh.metadata.update({'xaf_object':nod['name'],'xaf_material':mn,'xaf_texture':tex})
            # Object transform lives on parent object node; geometry is identity child.
            safe=re.sub(r'[^A-Za-z0-9_]+','_',mn)
            child=f'{name}__mesh' if len(groups)==1 else f'{name}__{safe}'
            scene.add_geometry(mesh,node_name=child,geom_name=child,parent_node_name=name,transform=np.eye(4))
            primitive_stats.append({'object':nod['name'],'object_node':name,'node':child,'parent_object':objrec['parent'],
                                    'material':mn,'texture':tex,'resolved_png':resolve_texture(tex,tex_idx).name if resolve_texture(tex,tex_idx) else None,
                                    'legacy_colorkey':material_alpha.get(mn)=='MASK','alpha_mode':material_alpha.get(mn,'OPAQUE'),
                                    'uv_correction':uv_correction,
                                    'source_uv_count':len(source_uv),
                                    'source_uv_sha256':source_uv_sha256,
                                    'export_input_uv_sha256':export_input_uv_sha256,
                                    'corner_vertices':len(ov),'triangles':len(of),'bad_uv_corners':bad_uv,'bad_normal_corners':bad_normal})
            objrec['primitive_count']+=1; objrec['corner_vertices']+=len(ov); objrec['triangles']+=len(of)
            objrec['bad_uv_corners']+=bad_uv; objrec['bad_normal_corners']+=bad_normal
        object_stats.append(objrec)

    # Compute world pivots from the final scene graph for evidence/debugging.
    for o in object_stats:
        try:
            T,_=scene.graph[o['scene_node']]; o['pivot_world']=T[:3,3].tolist()
        except Exception: pass
    return scene,object_stats,primitive_stats,mats,sorted(resolved),sorted(missing)


def main():
    import argparse
    ap=argparse.ArgumentParser(description='OpenAzrael XAF->GLB exporter v9')
    ap.add_argument('input_xaf',type=Path); ap.add_argument('decoded_texture_dir',type=Path); ap.add_argument('output_glb',type=Path)
    ap.add_argument('manifest',type=Path,nargs='?')
    ap.add_argument('--legacy-ir',type=Path,help='legacy_world_ir.json generated by export_legacy_world_v21.py')
    ap.add_argument('--room-id',type=int,help='Original demo room ID; embeds matching ambient emitter evidence in manifest')
    a=ap.parse_args(); src,td,out=a.input_xaf,a.decoded_texture_dir,a.output_glb; manifest=a.manifest or out.with_suffix('.manifest.json')
    scene,objs,prims,mats,resolved,missing=parse(src,td); scene.export(out)
    report={'source':src.name,'exporter_version':9,'object_count_all_levels':len(objs),'top_level_object_count':sum(o['depth']==0 for o in objs),
            'nested_object_count':sum(o['depth']>0 for o in objs),'primitive_count':len(prims),
            'corner_vertices':sum(x['corner_vertices'] for x in prims),'triangles':sum(x['triangles'] for x in prims),
            'textured_primitives':sum(x['resolved_png'] is not None for x in prims),'resolved_textures':resolved,'missing_textures':missing,
            'materials':mats,'objects':objs,'primitives':prims,
            'format_correction_v9':'Explicit untextured source colour alpha below 1.0 is exported with glTF alphaMode=BLEND; geometry, hierarchy and UV semantics remain v8-compatible.',
            'format_correction_v8':'Exporter can attach engine-neutral legacy spatial-audio evidence to the room manifest without converting or guessing source coordinates.',
            'format_correction_v7':'XAF object declarations can be nested. Child matrices are local to parent objects. v7 preserves the full object hierarchy instead of skipping nested objects.',
            'format_correction_v6':'face pairs are (vertex_index, normal_index); UVs are per-vertex; face_materials are per polygon'}
    if a.legacy_ir is not None:
        legacy=json.loads(a.legacy_ir.read_text(encoding='utf8'))
        report['legacy_coordinate_model']=legacy.get('coordinate_model')
        if a.room_id is not None:
            report['legacy_room_id']=a.room_id
            report['legacy_ambient_emitters']=[e for e in legacy.get('audio',{}).get('ambient_emitters',[]) if e.get('room_id')==a.room_id]
        report['legacy_ir_source']=a.legacy_ir.name
    manifest.write_text(json.dumps(report,indent=2))
    print(json.dumps({k:report[k] for k in ['source','object_count_all_levels','top_level_object_count','nested_object_count','primitive_count','triangles','textured_primitives','missing_textures']},indent=2))
    print('bad UV',sum(x['bad_uv_corners'] for x in prims),'bad normals',sum(x['bad_normal_corners'] for x in prims),'->',out)

if __name__=='__main__': main()
