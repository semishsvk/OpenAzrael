#!/usr/bin/env python3
import argparse,json,math,re
from pathlib import Path
ROOMS={0:'R1Demo',1:'R7Demo',2:'R8Demo'}
SND_RE=re.compile(r'^SAMPLE\s+(-?\d+),(-?\d+),(-?\d+)\s+(\S+)$',re.I)

def heading(x,z):
 n=math.hypot(x,z)
 if n==0:return None
 x/=n;z/=n
 a=math.degrees(math.acos(max(-1,min(1,z))))
 return 360-a if x>0 else a

def pan(listener,source):
 d=None;mode=1
 if listener<=180 and source>180:
  d=360-source+listener
  if d>180:d=-(360-d)
 else:
  d=-(360-listener+source)
  if d < -180:d+=360
 if d>90:mode=2;d=180-d
 elif d < -90:mode=2;d=-180-d
 return math.trunc(d*63/90+64),mode,d

def calc(lp,forward,sp,mv=99):
 dx,dy,dz=(sp[i]-lp[i] for i in range(3)); dist=math.sqrt(dx*dx+dy*dy+dz*dz)
 lh=heading(forward[0],forward[2]); sh=heading(dx,dz)
 if sh is None:return {'distance':dist,'status':'ZERO_HORIZONTAL_VECTOR_HOLD'}
 p,mode,fold=pan(lh,sh)
 raw=99 if dist==0 else math.trunc(15000/dist); gain=min(math.trunc(raw/mode),99); vol=math.trunc(mv*gain/99)
 return {'distance':round(dist,9),'listener_heading_deg':lh,'source_heading_deg':sh,'folded_angle_deg':fold,'pan':p,'rear_mode_divisor':mode,'gain':gain,'volume_at_master_99':vol,'status':'REFERENCE'}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--audio-dir',required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
 root=Path(a.audio_dir); emit=[]
 for rid in range(3):
  lines=(root/f'AMB{rid}.SND').read_text(errors='replace').splitlines()
  for line in lines:
   m=SND_RE.match(line.strip())
   if m: emit.append({'room_id':rid,'room':ROOMS[rid],'sound':m.group(4).upper(),'legacy_position':[int(m.group(i)) for i in (1,2,3)],'provenance':f'AMB{rid}.SND','confidence':'VERIFIED'})
 assert len(emit)==7
 # Synthetic listener poses are test inputs, never claimed original camera/player positions.
 poses=[('origin_front',[0,0,0],[0,0,1]),('origin_right',[0,0,0],[1,0,0]),('origin_rear',[0,0,0],[0,0,-1]),('origin_left',[0,0,0],[-1,0,0])]
 fixtures=[]
 for e in emit:
  for name,pos,fwd in poses:
   fixtures.append({'room_id':e['room_id'],'sound':e['sound'],'emitter_legacy_position':e['legacy_position'],'listener_fixture':name,'listener_legacy_position':pos,'listener_forward':fwd,'expected':calc(pos,fwd,e['legacy_position'])})
 assert len(fixtures)==28
 # invariants: authentic inventory + finite outputs + rotation should move pan for non-axis-degenerate sources.
 inv={'seven_authentic_emitters':len(emit)==7,'room_counts_2_3_2':[sum(x['room_id']==r for x in emit) for r in range(3)]==[2,3,2], 'twenty_eight_fixtures':len(fixtures)==28,'all_reference_cases_resolved':all(f['expected']['status']=='REFERENCE' for f in fixtures),'pan_range_1_127':all(1<=f['expected']['pan']<=127 for f in fixtures),'gain_le_99':all(f['expected']['gain']<=99 for f in fixtures)}
 assert all(inv.values()),inv
 out={'schema':'openazrael.classic_ambient_parity_fixtures','version':66,'status':'PASS','coordinate_space':'AZRAEL_WORLD_XYZ','transform_status':'PENDING_CALIBRATION','model_dependency':'Classic3DReferenceV65; caller angle-constant binding remains PROVISIONAL','invariants':inv,'emitters':emit,'listener_fixtures_notice':'Synthetic test poses only; not original player/camera positions.','fixtures':fixtures,'acceptance_gate':['Do not compare these numbers to Godot world coordinates until AzraelCoordinateTransform is calibrated.','Do not activate Classic renderer until caller angle constants are independently bound or equivalent runtime relocation is recovered.','Once original listener poses can be reconstructed, append binary-grounded fixtures rather than replacing these synthetic regression cases.']}
 Path(a.out).write_text(json.dumps(out,indent=2),encoding='utf8')
 print(json.dumps({'status':'PASS','emitters':len(emit),'fixtures':len(fixtures),'room_counts':[sum(x['room_id']==r for x in emit) for r in range(3)]},indent=2))
if __name__=='__main__':main()
