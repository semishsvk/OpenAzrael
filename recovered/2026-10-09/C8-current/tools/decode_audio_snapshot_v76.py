#!/usr/bin/env python3
import argparse, json, struct
from pathlib import Path

def i16(b,o): return struct.unpack_from('<h',b,o)[0]
def u16(b,o): return struct.unpack_from('<H',b,o)[0]
def u32(b,o): return struct.unpack_from('<I',b,o)[0]
def f32(b,o): return struct.unpack_from('<f',b,o)[0]

def main():
    ap=argparse.ArgumentParser(description='Decode independently captured OpenAzrael/Azrael runtime audio-manager and emitter dumps.')
    ap.add_argument('--manager',required=True); ap.add_argument('--emitters',required=True); ap.add_argument('--out',required=True)
    a=ap.parse_args(); m=Path(a.manager).read_bytes(); e=Path(a.emitters).read_bytes()
    if len(m)<0x364: raise SystemExit('manager dump must contain at least 0x364 bytes')
    if len(e)<7*24: raise SystemExit('emitter dump must contain at least 168 bytes')
    capacity=u16(m,0x1a4); count=u16(m,0x1a6)
    pool=[]
    for idx in range(min(capacity,8)):
        o=idx*36
        pool.append({'pool_index':idx,'miles_handle':f'0x{u32(m,o+4):08X}','sample_position':u32(m,o+8),'pan':u32(m,o+0x0c),'playback_rate':u32(m,o+0x10),'volume':u32(m,o+0x1c)})
    emit=[]
    for slot in range(7):
        o=slot*24; idx=i16(e,o+0x0c)
        rec={'emitter_slot':slot,'xyz':[f32(e,o),f32(e,o+4),f32(e,o+8)],'pool_index':idx}
        if 0<=idx<len(pool): rec['miles_handle']=pool[idx]['miles_handle']
        else: rec['miles_handle']=None
        emit.append(rec)
    out={'schema':'openazrael.runtime_audio_snapshot.observation','version':76,'observation_status':'OBSERVED_FROM_DUMPS','manager':{'capacity':capacity,'active_count':count,'bytes':len(m)},'pool':pool,'emitters':emit,'warning':'OBSERVED_FROM_DUMPS means values came from supplied binary dumps; it does not assert the dumps came from an original R.EXE run. Preserve capture provenance externally.'}
    Path(a.out).write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'status':'PASS','capacity':capacity,'active_count':count,'pool_records':len(pool),'emitters':len(emit),'joined_handles':sum(x['miles_handle'] is not None for x in emit)},indent=2))
if __name__=='__main__': main()
