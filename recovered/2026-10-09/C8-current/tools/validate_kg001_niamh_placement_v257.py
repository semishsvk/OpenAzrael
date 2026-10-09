#!/usr/bin/env python3
import json, sys
from pathlib import Path
import numpy as np, trimesh
ROOT=Path(__file__).resolve().parents[1]
scene=trimesh.load(ROOT/"assets/rooms/R7.glb",force="scene")
t,_=scene.graph["nibody__mesh"]
anchor=np.asarray(t[:3,3],float)
expected=np.array([-107.138,-34.5992,63.9427])
frame0=anchor+np.array([0.1451482,-92.2139,-0.04720965])
rest=anchor+np.array([0.1451639,-11.8114,-0.04719957])
wt,wg=scene.graph["well_floor__mesh"]; geom=scene.geometry[wg]
v=np.c_[geom.vertices,np.ones(len(geom.vertices))]; world=(wt@v.T).T[:,:3]
lo,hi=world.min(0),world.max(0)
room=(ROOT/"scripts/room_manager.gd").read_text()
checks={
 "raw_nibody_anchor_exact":np.max(np.abs(anchor-expected))<1e-3,
 "frame0_below_well":frame0[1] < lo[1]-50,
 "rest_intersects_well_vertical_band":lo[1] <= rest[1] <= hi[1],
 "source_anchor_runtime":"character_root.global_position = target.global_position" in room,
 "no_height33_translation":"+ 33.0" not in room,
 "no_proxy_bounds_center":"proxy_center.x" not in room,
}
checks={k:bool(v) for k,v in checks.items()}
failed=[k for k,v in checks.items() if not v]
out={"schema":"openazrael.kg001.niamh_placement","version":257,"status":"PASS" if not failed else "FAIL","anchor":anchor.tolist(),"frame0_nibelly_world":frame0.tolist(),"rest_nibelly_world":rest.tolist(),"well_floor_y":[float(lo[1]),float(hi[1])],"checks":checks,"failed":failed}
print(json.dumps(out,indent=2)); sys.exit(1 if failed else 0)
