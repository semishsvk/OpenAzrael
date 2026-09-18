#!/usr/bin/env python3
import argparse,json,pathlib,sys

def compare_record(r):
    cases=[]
    for e in r.get('emitters',[]):
        ref=e.get('openazrael_reference',{})
        obs=e.get('original_observation',{})
        status=obs.get('status','UNOBSERVED')
        c={'room_id':r.get('room_id'),'slot':e.get('legacy_3d_slot'),'node':e.get('node'),'observation_status':status,'comparable':False,'pass':None}
        if status=='OBSERVED' and obs.get('pan') is not None and obs.get('volume') is not None:
            c['comparable']=True
            c['expected_pan']=ref.get('pan'); c['observed_pan']=obs.get('pan')
            c['expected_volume']=ref.get('volume'); c['observed_volume']=obs.get('volume')
            c['pan_delta']=int(obs['pan'])-int(ref['pan'])
            c['volume_delta']=int(obs['volume'])-int(ref['volume'])
            c['pass']=(c['pan_delta']==0 and c['volume_delta']==0)
        cases.append(c)
    return cases

def main():
    ap=argparse.ArgumentParser(description='Compare independently observed original-demo pan/volume against OpenAzrael v71 reference captures.')
    ap.add_argument('capture',type=pathlib.Path)
    ap.add_argument('--out',type=pathlib.Path)
    a=ap.parse_args()
    records=[]
    for n,line in enumerate(a.capture.read_text().splitlines(),1):
        if line.strip():
            r=json.loads(line); records.append(r)
    cases=[c for r in records for c in compare_record(r)]
    comparable=[c for c in cases if c['comparable']]
    failed=[c for c in comparable if not c['pass']]
    out={'schema':'openazrael.audio_runtime_parity_comparison','version':71,'records':len(records),'cases':len(cases),'comparable_cases':len(comparable),'exact_matches':sum(c['pass'] is True for c in comparable),'failures':len(failed),'status':'PASS' if comparable and not failed else ('NO_OBSERVATIONS' if not comparable else 'FAIL'),'cases_detail':cases,'gate':'Do not promote live Classic playback from original-demo parity unless independently observed pan and volume match the reference across representative orientations/distances.'}
    text=json.dumps(out,indent=2)+'\n'
    if a.out: a.out.write_text(text)
    print(out['status'],out['exact_matches'],'/',out['comparable_cases'],'observed exact matches')
    return 1 if failed else 0
if __name__=='__main__': raise SystemExit(main())
