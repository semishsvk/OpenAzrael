from pathlib import Path
import re, sys, json
import numpy as np
import trimesh
from PIL import Image


def brace_block(text, start):
    op = text.find('{', start); d = 1; i = op + 1
    while d and i < len(text):
        d += (text[i] == '{') - (text[i] == '}'); i += 1
    return text[op+1:i-1], i


def named_blocks(text, kw):
    pat = re.compile(r'\b' + re.escape(kw) + r'\s+"([^"]+)"\s*\{', re.I); pos = 0
    while (m := pat.search(text, pos)):
        b, e = brace_block(text, m.start()); yield m.group(1), b; pos = e


def section(body, name):
    m = re.search(r'\b' + re.escape(name) + r'\s*\{', body, re.I)
    return brace_block(body, m.start())[0] if m else None


def nums(s):
    return [float(x) for x in re.findall(r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?', s)]


def material_table(t):
    out = {}
    for name, b in named_blocks(t, 'material'):
        mt = re.search(r'\btexture\s+"([^"]+)"', b, re.I)
        mc = section(b, 'colour')
        vals = nums(mc) if mc else []
        out[name] = {'texture': mt.group(1) if mt else None,
                     'colour': vals[:4] if len(vals) >= 4 else None}
    return out


def texture_index(texture_dir):
    return {p.stem.upper(): p for p in Path(texture_dir).glob('*.png')}


def resolve_texture(tex_name, idx):
    return idx.get(Path(tex_name).stem.upper()) if tex_name else None


def parse(src, texture_dir):
    src = Path(src); t = src.read_text('latin1')
    mats = material_table(t); scene = trimesh.Scene(); stats = []
    tex_idx = texture_index(texture_dir)
    missing = set(); resolved = set(); material_cache = {}

    def get_material(mn):
        if mn in material_cache: return material_cache[mn]
        md = mats.get(mn, {}); tex_name = md.get('texture'); tex_path = resolve_texture(tex_name, tex_idx)
        if tex_name and tex_path is None: missing.add(tex_name)
        if tex_path is not None:
            resolved.add(tex_path.name)
            mat = trimesh.visual.material.SimpleMaterial(image=Image.open(tex_path).convert('RGB'), name=mn)
        else:
            col = md.get('colour')
            rgba = [max(0,min(255,round(x*255))) for x in col[:4]] if col else [180,180,180,255]
            mat = trimesh.visual.material.SimpleMaterial(diffuse=rgba, name=mn)
        material_cache[mn] = mat; return mat

    for name, b in named_blocks(t, 'object'):
        meshb = section(b, 'mesh')
        if not meshb: continue
        vs, ns, us, fs = section(meshb,'vertices'), section(meshb,'normals'), section(meshb,'texture_coordinates'), section(meshb,'faces')
        if not vs or not fs: continue
        v = np.array(nums(vs),float).reshape(-1,3)
        n = np.array(nums(ns),float).reshape(-1,3) if ns else np.zeros((0,3))
        uv = np.array(nums(us),float).reshape(-1,2) if us else np.zeros((0,2))
        M = np.eye(4)
        ms = section(b,'matrix')
        if ms and len(nums(ms)) >= 16: M = np.array(nums(ms)[:16]).reshape(4,4)
        v_world = (np.c_[v,np.ones(len(v))] @ M)[:,:3]
        if len(n):
            A=M[:3,:3]
            try: Nmat=np.linalg.inv(A).T
            except np.linalg.LinAlgError: Nmat=A
            n_world=n@Nmat
            lens=np.linalg.norm(n_world,axis=1); lens[lens==0]=1; n_world/=lens[:,None]
        else: n_world=n

        # Critical XAF correction (v4): each face corner pair is (vertex_index, normal_index).
        # Texture coordinates are per vertex, not indexed by the second value. In all demo room
        # meshes that have UVs, texture_coordinate count == vertex count.
        ov, on, ouv, of = [], [], [], []
        bad_uv = 0; bad_normal = 0
        for line in fs.splitlines():
            z=[int(x) for x in re.findall(r'-?\d+',line)]
            if not z or z[0] < 3: continue
            count, p = z[0], z[1:]
            if len(p) < 2*count: continue
            corners=[]
            for i in range(count):
                vi, ni = p[2*i], p[2*i+1]
                if not (0 <= vi < len(v_world)): continue
                corners.append(len(ov)); ov.append(v_world[vi])
                if len(uv) and vi < len(uv): ouv.append(uv[vi])
                else: ouv.append([0.,0.]); bad_uv += 1 if len(uv) else 0
                if len(n_world) and 0 <= ni < len(n_world): on.append(n_world[ni])
                else: on.append([0.,1.,0.]); bad_normal += 1 if len(n_world) else 0
            if len(corners) != count: continue
            for i in range(1,count-1): of.append([corners[0],corners[i],corners[i+1]])
        if not of: continue

        mm=re.search(r'\bmaterial\s+"([^"]+)"',meshb,re.I); mn=mm.group(1) if mm else 'DEFAULT'
        tex=mats.get(mn,{}).get('texture')
        visual=trimesh.visual.TextureVisuals(uv=np.array(ouv,float),material=get_material(mn))
        mesh=trimesh.Trimesh(vertices=np.array(ov),faces=np.array(of),vertex_normals=np.array(on),visual=visual,process=False)
        mesh.metadata.update({'xaf_object':name,'xaf_material':mn,'xaf_texture':tex})
        scene.add_geometry(mesh,node_name=name,geom_name=name)
        stats.append({'object':name,'corner_vertices':len(ov),'triangles':len(of),'material':mn,'texture':tex,
                      'resolved_png':resolve_texture(tex,tex_idx).name if resolve_texture(tex,tex_idx) else None,
                      'uv_count_source':len(uv),'vertex_count_source':len(v),'normal_count_source':len(n),
                      'bad_uv_corners':bad_uv,'bad_normal_corners':bad_normal})
    return scene,stats,mats,sorted(resolved),sorted(missing)


def main():
    if len(sys.argv)<4: raise SystemExit('usage: export_xaf_glb_v4.py input.XAF decoded_texture_dir output.glb [manifest.json]')
    src,td,out=map(Path,sys.argv[1:4]); manifest=Path(sys.argv[4]) if len(sys.argv)>4 else out.with_suffix('.manifest.json')
    scene,st,mats,resolved,missing=parse(src,td); scene.export(out)
    report={'source':src.name,'mesh_count':len(st),'corner_vertices':sum(x['corner_vertices'] for x in st),
            'triangles':sum(x['triangles'] for x in st),'textured_meshes':sum(x['resolved_png'] is not None for x in st),
            'resolved_textures':resolved,'missing_textures':missing,'materials':mats,'objects':st,
            'format_correction':'XAF face pairs are (vertex_index, normal_index); UVs are per-vertex'}
    manifest.write_text(json.dumps(report,indent=2))
    print(json.dumps({k:report[k] for k in ['source','mesh_count','corner_vertices','triangles','textured_meshes','missing_textures']},indent=2))
    print('bad UV corners',sum(x['bad_uv_corners'] for x in st),'bad normal corners',sum(x['bad_normal_corners'] for x in st),'->',out)

if __name__=='__main__': main()
