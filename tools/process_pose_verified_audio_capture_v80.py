#!/usr/bin/env python3
import argparse,json,re,struct,math
from pathlib import Path
PAN=re.compile(r'AIL_set_sample_pan\(0x([0-9A-Fa-f]+),\s*(-?\d+)\)')
VOL=re.compile(r'AIL_set_sample_volume\(0x([0-9A-Fa-f]+),\s*(-?\d+)\)')
def u16(b,o): return struct.unpack_from('<H',b,o)[0]
def u32(b,o): return struct.unpack_from('<I',b,o)[0]
def i16(b,o): return struct.unpack_from('<h',b,o)[0]
def vec3(p):
 b=Path(p).read_bytes()
 if len(b)<12: raise SystemExit(f'{p}: need at least 12 bytes')
 return list(struct.unpack_from('<fff',b,0))
def dist(a,b): return math.sqrt(sum((float(x)-float(y))**2 for x,y in zip(a,b)))
def norm(a): return math.sqrt(sum(float(x)**2 for x in a))
def parse_trace(path,start,end):
 lines=Path(path).read_text(errors='replace').splitlines(); n=len(lines)
 lo=1 if start is None else start; hi=n if end is None else end
 if lo<1 or hi<lo or hi>n: raise SystemExit(f'invalid trace window {lo}..{hi}; log has {n} lines')
 latest={}; events=[]
 for lineno in range(lo,hi+1):
  line=lines[lineno-1]
  m=PAN.search(line)
  if m:
   h=int(m.group(1),16); v=int(m.group(2)); latest.setdefault(h,{})['pan']=v; events.append((lineno,'pan',h,v)); continue
  m=VOL.search(line)
  if m:
   h=int(m.group(1),16); v=int(m.group(2)); latest.setdefault(h,{})['volume']=v; events.append((lineno,'volume',h,v))
 return latest,events,{'start_line':lo,'end_line':hi,'total_lines':n,'bounded':start is not None and end is not None}
def main():
 ap=argparse.ArgumentParser(description='v80 pose-verified original Azrael audio parity processor.')
 for x in ('manager','emitters','listener-position','listener-forward','miles-log','reference-capture','room-id','out'): ap.add_argument('--'+x,required=True)
 ap.add_argument('--trace-start-line',type=int); ap.add_argument('--trace-end-line',type=int)
 ap.add_argument('--position-tolerance',type=float,default=0.05); ap.add_argument('--forward-tolerance',type=float,default=0.002)
 a=ap.parse_args(); m=Path(a.manager).read_bytes(); e=Path(a.emitters).read_bytes()
 if len(m)<0x364: raise SystemExit('manager dump must contain at least 0x364 bytes')
 if len(e)<168: raise SystemExit('emitter dump must contain at least 168 bytes')
 orig_pos=vec3(a.listener_position); orig_fwd=vec3(a.listener_forward)
 cap=u16(m,0x1a4); count=u16(m,0x1a6)
 if cap>8: raise SystemExit(f'implausible sample-pool capacity {cap}; expected <=8')
 pool={i:u32(m,i*36+4) for i in range(cap)}
 latest,events,window=parse_trace(a.miles_log,a.trace_start_line,a.trace_end_line)
 slot_obs={}
 for slot in range(7):
  idx=i16(e,slot*24+0x0c); h=pool.get(idx); vals=latest.get(h,{}) if h is not None else {}
  ok=h is not None and 'pan' in vals and 'volume' in vals
  slot_obs[slot]={'status':'OBSERVED' if ok else 'UNOBSERVED','pan':vals.get('pan'),'volume':vals.get('volume'),'sample_pool_index':idx,'miles_handle':f'0x{h:X}' if h is not None else None,'mapping_provenance':'RUNTIME_EMITTER_POOL_JOIN_V74_V76'}
 records=[json.loads(x) for x in Path(a.reference_capture).read_text().splitlines() if x.strip()]
 candidates=[r for r in records if str(r.get('room_id'))==str(a.room_id)]
 if not candidates: raise SystemExit(f'no reference records for room_id={a.room_id!r}')
 scored=[]
 for r in candidates:
  lp=r.get('listener',{}).get('position'); lf=r.get('listener',{}).get('forward')
  if not (isinstance(lp,list) and len(lp)==3 and isinstance(lf,list) and len(lf)==3): continue
  scored.append((dist(orig_pos,lp),dist(orig_fwd,lf),r))
 if not scored: raise SystemExit('reference records have no usable listener pose')
 scored.sort(key=lambda x:(x[0],x[1])); pd,fd,selected=scored[0]
 pose_ok=pd<=a.position_tolerance and fd<=a.forward_tolerance
 fwd_norm=norm(orig_fwd); fwd_norm_ok=abs(fwd_norm-1.0)<=0.01
 cases=[]
 for em in selected.get('emitters',[]):
  s=em.get('legacy_3d_slot'); obs=slot_obs.get(s,{}) if isinstance(s,int) else {}; ref=em.get('openazrael_reference',{})
  c={'slot':s,'observation_status':obs.get('status','UNOBSERVED'),'pass':None}
  if pose_ok and window['bounded'] and fwd_norm_ok and obs.get('status')=='OBSERVED' and ref.get('pan') is not None and ref.get('volume') is not None:
   c.update(expected_pan=ref['pan'],observed_pan=obs['pan'],expected_volume=ref['volume'],observed_volume=obs['volume'])
   c['pan_delta']=int(obs['pan'])-int(ref['pan']); c['volume_delta']=int(obs['volume'])-int(ref['volume']); c['pass']=c['pan_delta']==0 and c['volume_delta']==0
  cases.append(c)
 comparable=[c for c in cases if c['pass'] is not None]; failures=[c for c in comparable if not c['pass']]
 blockers=[]
 if not pose_ok: blockers.append('POSE_MISMATCH')
 if not fwd_norm_ok: blockers.append('ORIGINAL_FORWARD_NOT_UNIT')
 if not window['bounded']: blockers.append('TRACE_WINDOW_UNBOUNDED')
 if not comparable and not blockers: blockers.append('NO_COMPARABLE_OBSERVATIONS')
 status='PASS' if comparable and not failures and not blockers else ('FAIL' if failures else 'NOT_EVIDENCE_READY')
 out={'schema':'openazrael.pose_verified_original_audio_parity','version':80,'status':status,'room_id':a.room_id,'evidence_blockers':blockers,'original_listener':{'position':orig_pos,'forward':orig_fwd,'forward_norm':fwd_norm},'matched_reference_listener':selected.get('listener'),'pose_delta':{'position':pd,'forward':fd,'position_tolerance':a.position_tolerance,'forward_tolerance':a.forward_tolerance,'pass':pose_ok},'trace_window':window,'manager':{'capacity':cap,'active_count':count},'trace_events_in_window':len(events),'runtime_slot_observations':slot_obs,'comparable_cases':len(comparable),'exact_matches':sum(c['pass'] is True for c in comparable),'failures':len(failures),'cases':cases,'evidence_boundary':'PASS requires a bounded AIL trace window, an independently dumped original listener pose matching the selected OpenAzrael F9 pose, and runtime emitter→pool→Miles-handle joins. Unbounded logs or pose mismatch cannot produce parity evidence.'}
 Path(a.out).write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
 print(json.dumps({'status':status,'blockers':blockers,'pose_position_delta':pd,'pose_forward_delta':fd,'trace_window_bounded':window['bounded'],'comparable_cases':len(comparable),'exact_matches':out['exact_matches'],'failures':len(failures)},indent=2))
 return 1 if failures else 0
if __name__=='__main__': raise SystemExit(main())
