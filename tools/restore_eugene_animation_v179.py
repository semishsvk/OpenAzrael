#!/usr/bin/env python3
"""Restore Eugene/EugenB source character models and ANI-defined clips from canonical ATDEMO.

Commercial source payloads remain outside Git. This restorer is intentionally
fail-closed on known source structure; source SHA fingerprints are not invented.
"""
from pathlib import Path
import argparse, hashlib, json, sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/"tools/texture_pipeline"))
from tools.remaster_framework.source_registry import resolve_source
from tools.restore_character_animation_v166 import ranges, animation_set, node_paths, write_clip
from export_xaf_glb_v8 import parse

SPECS={
 "EugenB":{"xaf":"EUGBLD.XAF","xaf_sha256":"0004eaac87202d2487c72f43008cf5c6cec15241d07a95dc550737889d5bb62f","ani":"EUGENB.ANI","ani_sha256":"4125d9693137f74020209fc2f7f834cb64ce232cbabd4e7a8fe0199d9933b636","census":{"animated_nodes":30,"frame_min":0,"frame_max":163,"rotation_keys":849,"scale_keys":199,"position_keys":275}},
 "Eugene":{"xaf":"EUGENE.XAF","xaf_sha256":"1533e24af2729f6a9ccbc4e791fec92617b44f709a3f1dc31ce7a71763be51af","ani":"EUGENE.ANI","ani_sha256":"4125d9693137f74020209fc2f7f834cb64ce232cbabd4e7a8fe0199d9933b636","census":None},
}
REQUIRED={"REST":(0,0),"RUN":(2,7),"ATTACK":(53,70),"SHOT":(130,163),"DEATH_TWITCH":(160,163),"DEAD":(163,163)}

def key_stats(aset):
    frames=[]
    counts={"rotation_keys":0,"scale_keys":0,"position_keys":0}
    for rec in aset.values():
        for sec,key in (("rotate_keys","rotation_keys"),("scale_keys","scale_keys"),("position_keys","position_keys")):
            rows=rec[sec]; counts[key]+=len(rows); frames.extend(int(r[0]) for r in rows)
    return {"animated_nodes":len(aset),"frame_min":min(frames) if frames else -1,"frame_max":max(frames) if frames else -1,**counts}

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("demo_dir",type=Path,nargs="?")
    ap.add_argument("--source-home",type=Path)
    ap.add_argument("--fps",type=float,default=15.0)
    ap.add_argument("--manifest",type=Path,default=ROOT/".tmp/kg001/eugene_animation_restore_v179.json")
    a=ap.parse_args()
    src=a.demo_dir.resolve() if a.demo_dir else resolve_source("demo",home=a.source_home)
    report={"schema":"openazrael.kg001.eugene_animation_restore","version":179,"status":"PASS","fps":a.fps,
            "fps_status":"PROVISIONAL_CALIBRATION_NOT_SOURCE_PROVEN","characters":{}}
    for character,spec in SPECS.items():
        xaf=src/"TEXTURES"/spec["xaf"]; ani=src/spec["ani"]
        if not xaf.is_file() or not ani.is_file(): raise FileNotFoundError(f"{spec['xaf']}/{spec['ani']}")
        observed_xaf_sha=hashlib.sha256(xaf.read_bytes()).hexdigest()
        observed_ani_sha=hashlib.sha256(ani.read_bytes()).hexdigest()
        if observed_xaf_sha != spec["xaf_sha256"] or observed_ani_sha != spec["ani_sha256"]:
            raise ValueError((character,"CANONICAL_SOURCE_FINGERPRINT_MISMATCH",observed_xaf_sha,observed_ani_sha))
        text=xaf.read_text("latin1"); aset=animation_set(text); paths=node_paths(text); rr=ranges(ani)
        if not rr:
            raise ValueError((character,"ANI_HAS_NO_RANGES"))
        for name,bounds in REQUIRED.items():
            if name in rr and rr[name]!=bounds:
                raise ValueError((character,name,rr.get(name),bounds))
        stats=key_stats(aset)
        if spec["census"] is not None and stats!=spec["census"]: raise ValueError((character,"census",stats,spec["census"]))
        for name,(start,end) in rr.items():
            if start < stats["frame_min"] or end > stats["frame_max"] or end < start:
                raise ValueError((character,"ANI_RANGE_OUTSIDE_XAF",name,(start,end),(stats["frame_min"],stats["frame_max"])))
        out_root=ROOT/"assets/characters"/character; out_root.mkdir(parents=True,exist_ok=True)
        for stale in out_root.glob("*.tres"):
            stale.unlink()
        scene,objs,prims,mats,resolved,missing=parse(xaf,ROOT/"assets/textures/classic")
        if missing: raise ValueError((character,"missing textures",missing))
        glb=out_root/(character+".glb"); scene.export(glb)
        tracks={k:{**v,"path":paths[k]} for k,v in aset.items()}
        clips={}
        for name,(start,end) in rr.items():
            out=out_root/(name+".tres")
            clips[name]={"range":[start,end],"track_count":write_clip(out,name,start,end,tracks,a.fps),
                         "sha256":hashlib.sha256(out.read_bytes()).hexdigest()}
        report["characters"][character]={
            "source_xaf":spec["xaf"],"source_xaf_sha256":observed_xaf_sha,
            "source_ani":spec["ani"],"source_ani_sha256":observed_ani_sha,
            "source_fingerprint_status":"PINNED_CANONICAL_ATDEMO",
            "census":stats,"ani_ranges":{k:list(v) for k,v in sorted(rr.items())},
            "stale_clip_policy":"DELETE_BEFORE_SOURCE_EXPORT",
            "ani_xaf_range_validation":"PASS",
            "model":str(glb.relative_to(ROOT)).replace("\\","/"),
            "model_sha256":hashlib.sha256(glb.read_bytes()).hexdigest(),"clips":clips}
    a.manifest.parent.mkdir(parents=True,exist_ok=True)
    a.manifest.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2))
    return 0
if __name__=="__main__": raise SystemExit(main())
