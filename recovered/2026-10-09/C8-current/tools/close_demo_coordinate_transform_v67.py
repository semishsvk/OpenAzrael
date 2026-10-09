#!/usr/bin/env python3
import json, math, pathlib, hashlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
IR=ROOT/'data/audio/legacy_world_ir.json'; CAL=ROOT/'data/audio/coordinate_calibration_v22.json'
out=ROOT/'data/audio/demo_coordinate_closure_v67.json'
ir=json.loads(IR.read_text()); cal=json.loads(CAL.read_text())
assert cal['conclusion']['demo_transform']=='IDENTITY'
# Cross-check all authentic ambient points are identity-mapped and in their room AABB.
amb=[]
for e in ir['audio']['ambient_emitters']:
    lp=e['legacy_position']; gp=e.get('godot_position')
    assert gp==lp
    room={0:'R1',1:'R7',2:'R8'}[e['room_id']]; lo,hi=cal['rooms'][room]['glb_bounds']
    inside=all(lo[i] <= lp[i] <= hi[i] for i in range(3)); assert inside
    amb.append({'id':e['emitter_id'],'room':room,'identity':True,'inside_room_aabb':inside})
# NPC state corpus lives in the same declared AZRAEL_WORLD_XYZ. Check geometric plausibility
# against R1 demo geometry and direction normalization before applying the already-calibrated demo identity.
lo,hi=cal['rooms']['R1']['glb_bounds']; npcs=[]
for n in ir['npc_state_instances']:
    p=n['legacy_position']; v=n['legacy_direction']; norm=math.sqrt(sum(x*x for x in v))
    inside=all(lo[i] <= p[i] <= hi[i] for i in range(3)); assert inside
    assert abs(norm-1.0) < 2e-5
    n['godot_position']=p.copy(); n['godot_direction']=v.copy(); n['transform_status']='CALIBRATED_DEMO_V67'
    n['transform_confidence']='HIGH'
    npcs.append({'file':n['source']['file'],'name':n['name'],'inside_R1_aabb':inside,'direction_norm':norm})
# Normalize per-room legacy IR files too; older snapshots still carried PENDING despite global IR being calibrated.
for room in ('R1','R7','R8'):
    path=ROOT/f'data/audio/{room}.legacy.json'; d=json.loads(path.read_text())
    for e in d['ambient_emitters']:
        e['godot_position']=e['legacy_position'].copy(); e['transform_status']='CALIBRATED_DEMO_V67'; e['transform_confidence']='HIGH'
    path.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
for e in ir['audio']['ambient_emitters']:
    e['godot_position']=e['legacy_position'].copy(); e['transform_status']='CALIBRATED_DEMO_V67'; e['transform_confidence']='HIGH'
ir['coordinate_model']['godot_transform'].update({'status':'CALIBRATED_DEMO_V67','confidence':'HIGH','evidence':'coordinate_calibration_v22.json + demo_coordinate_closure_v67.json','policy':'Identity is closed for demo R1/R7/R8 and demo NPC state corpus. Revalidate before declaring retail/full-game global transform.'})
IR.write_text(json.dumps(ir,indent=2,sort_keys=True)+'\n')
result={'schema':'openazrael.demo_coordinate_closure','version':67,'transform':{'expression':'Vector3(x, y, z)','scale':1.0,'axis_order':'XYZ','axis_sign':[1,1,1],'confidence':'HIGH','scope':'demo R1/R7/R8 + NPC state corpus','retail_global_status':'HOLD_PENDING_FULL_GAME_CROSS_VALIDATION'},'ambient_checks':amb,'npc_checks':npcs,'counts':{'ambient':len(amb),'npc_states':len(npcs)},'invariants':{'all_ambient_identity':True,'all_ambient_inside_room_aabb':True,'all_npc_inside_R1_aabb':True,'all_npc_directions_unit':True}}
out.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
print('v67 coordinate closure PASS:',len(amb),'ambient,',len(npcs),'NPC states')
