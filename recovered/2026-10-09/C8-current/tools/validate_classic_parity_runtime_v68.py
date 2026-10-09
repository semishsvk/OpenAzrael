#!/usr/bin/env python3
import json, math, pathlib, hashlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
src=json.loads((ROOT/'data/audio/classic_ambient_parity_v66.json').read_text())

def heading(x,z):
    n=math.hypot(x,z)
    if n==0: return None
    x/=n; z/=n
    a=math.degrees(math.acos(max(-1,min(1,z))))
    return 360-a if x>0 else a

def pan(l,s):
    mode=1
    if l<=180 and s>180:
        d=360-s+l
        if d>180: d=-(360-d)
    else:
        d=-(360-l+s)
        if d < -180: d+=360
    if d>90: mode=2; d=180-d
    elif d < -90: mode=2; d=-180-d
    return int(d*63/90+64),d,mode

def atten(dist,master,mode):
    raw=99 if dist==0 else int(15000/dist)
    gain=min(int(raw/mode),99)
    return int(master*gain/99),gain

fails=[]; cases=[]
for f in src['fixtures']:
    lp=f['listener_legacy_position']; fw=f['listener_forward']; sp=f['emitter_legacy_position']; e=f['expected']
    dx=sp[0]-lp[0]; dy=sp[1]-lp[1]; dz=sp[2]-lp[2]
    dist=math.sqrt(dx*dx+dy*dy+dz*dz)
    lh=heading(fw[0],fw[2]); sh=heading(dx,dz)
    pp,dd,mode=pan(lh,sh); vol,gain=atten(dist,99,mode)
    ok=(abs(dist-e['distance'])<1e-8 and abs(lh-e['listener_heading_deg'])<1e-8 and abs(sh-e['source_heading_deg'])<1e-8 and abs(dd-e['folded_angle_deg'])<1e-8 and pp==e['pan'] and mode==e['rear_mode_divisor'] and gain==e['gain'] and vol==e['volume_at_master_99'])
    if not ok: fails.append({'fixture':f['listener_fixture'],'sound':f['sound']})
    cases.append({'room_id':f['room_id'],'sound':f['sound'],'listener_fixture':f['listener_fixture'],'pass':ok})
out={'schema':'openazrael.classic_3d_runtime_shadow_validation','version':68,'status':'PASS' if not fails else 'FAIL','source_fixture_version':66,'coordinate_transform':'IDENTITY_HIGH_DEMO_V67','runtime_backend':'Classic3DParityBackendV68','playback_mutation':False,'master_volume_for_fixture':99,'fixture_count':len(cases),'pass_count':sum(x['pass'] for x in cases),'failures':fails,'cases':cases,'acceptance_gate':'Shadow backend must reproduce all v66 golden fixtures before it may be allowed to drive live Classic playback. Caller angle-constant binding remains PROVISIONAL.'}
text=json.dumps(out,indent=2)+"\n"
(ROOT/'data/audio/classic_3d_runtime_shadow_v68.json').write_text(text)
print(out['status'],out['pass_count'],'/',out['fixture_count'])
