#!/usr/bin/env python3
import argparse,json,re,struct
from pathlib import Path
PAN=re.compile(r'AIL_set_sample_pan\(0x([0-9A-Fa-f]+),\s*(-?\d+)\)')
VOL=re.compile(r'AIL_set_sample_volume\(0x([0-9A-Fa-f]+),\s*(-?\d+)\)')
def u16(b,o): return struct.unpack_from('<H',b,o)[0]
def u32(b,o): return struct.unpack_from('<I',b,o)[0]
def i16(b,o): return struct.unpack_from('<h',b,o)[0]
def parse_trace(p):
    latest={}; events=[]
    for n,line in enumerate(Path(p).read_text(errors='replace').splitlines(),1):
        m=PAN.search(line)
        if m:
            h=int(m.group(1),16); v=int(m.group(2)); latest.setdefault(h,{})['pan']=v; events.append((n,'pan',h,v)); continue
        m=VOL.search(line)
        if m:
            h=int(m.group(1),16); v=int(m.group(2)); latest.setdefault(h,{})['volume']=v; events.append((n,'volume',h,v))
    return latest,events
def main():
    ap=argparse.ArgumentParser(description='v79 one-command original Azrael audio parity processor: raw manager/emitter dumps + AIL_DEBUG trace + OpenAzrael F9 reference capture.')
    ap.add_argument('--manager',required=True); ap.add_argument('--emitters',required=True); ap.add_argument('--miles-log',required=True)
    ap.add_argument('--reference-capture',required=True,help='v71/F9 JSONL reference capture containing the same room/listener pose')
    ap.add_argument('--room-id',required=True,help='Room id exactly as stored in reference capture, e.g. R1 or 0')
    ap.add_argument('--out',required=True)
    a=ap.parse_args(); m=Path(a.manager).read_bytes(); e=Path(a.emitters).read_bytes()
    if len(m)<0x364: raise SystemExit('manager dump must contain at least 0x364 bytes')
    if len(e)<168: raise SystemExit('emitter dump must contain at least 168 bytes')
    cap=u16(m,0x1a4); count=u16(m,0x1a6)
    if cap>8: raise SystemExit(f'implausible sample-pool capacity {cap}; expected <=8')
    pool={i:u32(m,i*36+4) for i in range(cap)}
    latest,events=parse_trace(a.miles_log)
    slot_obs={}
    for slot in range(7):
        idx=i16(e,slot*24+0x0c)
        h=pool.get(idx)
        vals=latest.get(h,{}) if h is not None else {}
        status='OBSERVED' if h is not None and 'pan' in vals and 'volume' in vals else 'UNOBSERVED'
        slot_obs[slot]={'status':status,'pan':vals.get('pan'),'volume':vals.get('volume'),'capture_method':'ORIGINAL_R_EXE_AIL_DEBUG_PLUS_V76_SNAPSHOT','sample_pool_index':idx,'miles_handle':f'0x{h:X}' if h is not None else None,'mapping_provenance':'RUNTIME_EMITTER_POOL_JOIN_V74_V76'}
    records=[json.loads(x) for x in Path(a.reference_capture).read_text().splitlines() if x.strip()]
    room_s=str(a.room_id); selected=[]
    for r in records:
        if str(r.get('room_id'))!=room_s: continue
        rr=json.loads(json.dumps(r))
        for em in rr.get('emitters',[]):
            s=em.get('legacy_3d_slot')
            if isinstance(s,int) and s in slot_obs: em['original_observation']=slot_obs[s]
        selected.append(rr)
    if not selected: raise SystemExit(f'no reference records for room_id={room_s!r}')
    cases=[]
    for r in selected:
        for em in r.get('emitters',[]):
            ref=em.get('openazrael_reference',{}); obs=em.get('original_observation',{}); c={'room_id':r.get('room_id'),'slot':em.get('legacy_3d_slot'),'status':obs.get('status'),'pass':None}
            if obs.get('status')=='OBSERVED' and ref.get('pan') is not None and ref.get('volume') is not None:
                c.update(expected_pan=ref['pan'],observed_pan=obs['pan'],expected_volume=ref['volume'],observed_volume=obs['volume'])
                c['pan_delta']=int(obs['pan'])-int(ref['pan']); c['volume_delta']=int(obs['volume'])-int(ref['volume']); c['pass']=c['pan_delta']==0 and c['volume_delta']==0
            cases.append(c)
    comp=[c for c in cases if c['pass'] is not None]; fails=[c for c in comp if not c['pass']]
    status='PASS' if comp and not fails else ('NO_OBSERVATIONS' if not comp else 'FAIL')
    out={'schema':'openazrael.original_audio_parity_pipeline','version':79,'status':status,'room_id':a.room_id,'manager':{'capacity':cap,'active_count':count},'trace_events':len(events),'runtime_slot_observations':slot_obs,'reference_records':len(selected),'comparable_cases':len(comp),'exact_matches':sum(c['pass'] is True for c in comp),'failures':len(fails),'cases':cases,'evidence_boundary':'Slot→Miles-handle identity comes only from supplied runtime dumps. Pan/volume come only from supplied AIL_DEBUG trace. OpenAzrael reference values come only from the supplied F9 capture. No chronology-based identity guessing is performed.'}
    Path(a.out).write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'status':status,'trace_events':len(events),'comparable_cases':len(comp),'exact_matches':out['exact_matches'],'failures':len(fails)},indent=2))
    return 1 if fails else 0
if __name__=='__main__': raise SystemExit(main())
