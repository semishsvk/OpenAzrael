#!/usr/bin/env python3
"""Restore source-backed Azrael's Tear character model and XAF animation clips.

NIAMH.ANI defines named frame ranges. NIAMH.XAF contains the 19-node
animation_set (57 transform tracks / 268 source keys). This converter keeps
commercial payloads out of Git and emits ignored runtime assets only.
"""
from __future__ import annotations
from pathlib import Path
import argparse, hashlib, json, re, sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools/texture_pipeline"))
from export_xaf_glb_v8 import parse, all_object_nodes, direct_section, nums

ANI_RANGE_RE=re.compile(r"^([A-Z0-9_]+)\s+(\d+)\s*-\s*(\d+)\s*$",re.I)
ANIM_RE=re.compile(r'\banimation\s+"([^"]+)"\s*\{',re.I)

def brace(text,op):
    d=1;i=op+1
    while d and i<len(text):
        if text[i]=="{": d+=1
        elif text[i]=="}": d-=1
        i+=1
    if d: raise ValueError("unmatched brace")
    return i-1

def ranges(path):
    out={}
    for line in path.read_text("latin1").splitlines():
        m=ANI_RANGE_RE.match(line.strip())
        if m: out[m.group(1).upper()]=(int(m.group(2)),int(m.group(3)))
    return out

def animation_set(text):
    out={}
    for m in ANIM_RE.finditer(text):
        op=text.find("{",m.start(),m.end()+1); cl=brace(text,op); b=text[op+1:cl]
        om=re.search(r'\bobject_name\s+"([^"]+)"',b,re.I)
        if not om: continue
        rec={"object":om.group(1)}
        for sec,width in (("rotate_keys",5),("scale_keys",4),("position_keys",4)):
            s=direct_section(b,sec)
            a=nums(s) if s else []
            rec[sec]=[a[i:i+width] for i in range(0,len(a),width) if len(a[i:i+width])==width]
        out[rec["object"]]=rec
    return out

def node_paths(text):
    nodes=all_object_nodes(text)
    paths={}
    for i,n in enumerate(nodes):
        parts=[n["name"]]; p=n["parent_index"]
        while p is not None:
            parts.append(nodes[p]["name"]); p=nodes[p]["parent_index"]
        paths[n["name"]]="/".join(reversed(parts))
    return paths

def fmt(x): return f"{float(x):.9g}"
def vec3(v): return "Vector3("+", ".join(fmt(x) for x in v)+")"
def quat(v):
    # XAF rotate_keys are scalar-first (w,x,y,z); Godot Quaternion is x,y,z,w.
    w,x,y,z=v
    return "Quaternion("+", ".join(fmt(q) for q in (x,y,z,w))+")"

def clipped(keys,start,end):
    rows=[r for r in keys if start<=int(r[0])<=end]
    # Preserve boundary pose even when a channel has no authored key exactly at
    # clip start/end by carrying the nearest source sample, never inventing motion.
    if keys and not rows:
        before=[r for r in keys if int(r[0])<=start]
        after=[r for r in keys if int(r[0])>=start]
        r=(before[-1] if before else after[0])
        rows=[r]
    return rows

def write_clip(path,name,start,end,tracks,fps):
    lines=['[gd_resource type="Animation" format=3]','',
           '[resource]',f'resource_name = "{name}"',
           f'length = {fmt((end-start)/fps)}',f'loop_mode = {1 if name == "REST" else 0}']
    ti=0
    for obj,rec in tracks.items():
        np=rec["path"]
        for sec,typ,render in (("position_keys","position_3d",vec3),
                               ("rotate_keys","rotation_3d",quat),
                               ("scale_keys","scale_3d",vec3)):
            rows=clipped(rec[sec],start,end)
            if not rows: continue
            times=[max(0.0,(float(r[0])-start)/fps) for r in rows]
            vals=[render(r[1:]) for r in rows]
            lines += [
              f'tracks/{ti}/type = "{typ}"',
              f'tracks/{ti}/imported = true',
              f'tracks/{ti}/enabled = true',
              f'tracks/{ti}/path = NodePath("{np}")',
              f'tracks/{ti}/interp = 1',
              f'tracks/{ti}/loop_wrap = true',
              f'tracks/{ti}/keys = {{',
              '"times": PackedFloat32Array('+", ".join(fmt(x) for x in times)+'),',
              '"transitions": PackedFloat32Array('+", ".join("1" for _ in times)+'),',
              '"update": 0,',
              '"values": ['+", ".join(vals)+']',
              '}'
            ]
            ti+=1
    path.write_text("\n".join(lines)+"\n",encoding="utf-8")
    return ti

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("demo_dir",type=Path)
    ap.add_argument("--fps",type=float,default=15.0,
        help="XAF frame clock used for Godot seconds; default 15.0, override for runtime timing calibration.")
    ap.add_argument("--out-root",type=Path,default=ROOT/"assets/characters/Niamh")
    ap.add_argument("--manifest",type=Path,default=ROOT/".tmp/kg001/niamh_animation_restore_v166.json")
    a=ap.parse_args()
    src=a.demo_dir.resolve(); xaf=src/"TEXTURES/NIAMH.XAF"; ani=src/"NIAMH.ANI"
    if not xaf.is_file() or not ani.is_file(): raise FileNotFoundError("NIAMH.XAF/NIAMH.ANI")
    expected={"NIAMH.XAF":"6208e8831aa196b328b1c0f526765955e3eb0816e4a706f5c6c337c6c2708692","NIAMH.ANI":"36192765d8ecc4b61d5084efcf6ccb20cc8d3032ec4b415297a75af34f0e008c"}
    if hashlib.sha256(xaf.read_bytes()).hexdigest()!=expected["NIAMH.XAF"] or hashlib.sha256(ani.read_bytes()).hexdigest()!=expected["NIAMH.ANI"]:
        raise ValueError("canonical Niamh source fingerprint mismatch")
    text=xaf.read_text("latin1"); aset=animation_set(text); paths=node_paths(text); rr=ranges(ani)
    if (len(aset),sum(bool(r[s]) for r in aset.values() for s in ("rotate_keys","scale_keys","position_keys")),
        sum(len(r[s]) for r in aset.values() for s in ("rotate_keys","scale_keys","position_keys"))) != (19,57,268):
        raise ValueError("canonical NIAMH animation census mismatch")
    required={"NOLOOP1":(0,14),"REST":(15,41),"NOLOOP2":(42,57)}
    if any(rr.get(k)!=v for k,v in required.items()): raise ValueError(("NIAMH.ANI ranges",rr))
    a.out_root.mkdir(parents=True,exist_ok=True)
    scene,objs,prims,mats,resolved,missing=parse(xaf,ROOT/"assets/textures/classic")
    if missing: raise ValueError(("missing Niamh textures",missing))
    glb=a.out_root/"Niamh.glb"; scene.export(glb)
    tracks={k:{**v,"path":paths[k]} for k,v in aset.items()}
    clips={}
    for name,(start,end) in required.items():
        out=a.out_root/(name+".tres")
        clips[name]={"range":[start,end],"track_count":write_clip(out,name,start,end,tracks,a.fps)}
    a.manifest.parent.mkdir(parents=True,exist_ok=True)
    report={"schema":"openazrael.character_animation_restore","version":166,"status":"PASS",
      "source_xaf":"NIAMH.XAF","source_xaf_sha256":hashlib.sha256(xaf.read_bytes()).hexdigest(),
      "source_ani":"NIAMH.ANI","source_ani_sha256":hashlib.sha256(ani.read_bytes()).hexdigest(),
      "animated_nodes":19,"tracks":57,"keyframes":268,"fps":a.fps,"fps_status":"PROVISIONAL_CALIBRATION_NOT_SOURCE_PROVEN",
      "clips":clips,"model":"assets/characters/Niamh/Niamh.glb",
      "sequence":{"activation":["NOLOOP1","REST"],"conversation":"1A"},
      "note":"Frame ranges and transforms are source-exact; --fps remains an explicit calibration parameter."}
    a.manifest.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2))
if __name__=="__main__": raise SystemExit(main())
