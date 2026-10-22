#!/usr/bin/env python3
from pathlib import Path
import argparse, hashlib, json, struct, sys
sys.path.insert(0,'/tmp')
EXPECTED='381e4f5c61e4bb8c27f06b1944e6673bbebc39ca219cc08fb9f948da2ca37c00'
LE_OFFSET=0x37D4C
BIAS=0x2AA8

def u16(b,o): return struct.unpack_from('<H',b,o)[0]
def u32(b,o): return struct.unpack_from('<I',b,o)[0]
def build_objects(raw):
    le=raw[LE_OFFSET:]
    if le[:2]!=b'LE': raise SystemExit('LE header missing')
    ps=u32(le,0x28); ot=u32(le,0x40); oc=u32(le,0x44); pm=u32(le,0x48); dp=u32(le,0x80)
    out=[]
    for idx in range(oc):
        size,base,flags,first,count,_=struct.unpack_from('<IIIIII',le,ot+24*idx)
        span=bytearray(count*ps)
        for lp in range(count):
            e=le[pm+4*(first-1+lp):pm+4*(first-1+lp)+4]
            phys=(e[0]<<16)|(e[1]<<8)|e[2]
            if not phys: continue
            src=LE_OFFSET+dp+(phys-1)*ps; dst=lp*ps; n=min(ps,max(0,len(raw)-src)); span[dst:dst+n]=raw[src:src+n]
        out.append({'virtual':bytes(span[:size]),'page_span':bytes(span),'base':base,'size':size})
    return out

def call_target(b,site):
    if site<0 or site+5>len(b) or b[site]!=0xE8:return None
    return site+5+int.from_bytes(b[site+1:site+5],'little',signed=True)
def calls(b,target,lo=0,hi=None):
    hi=len(b) if hi is None else min(hi,len(b))
    return [i for i in range(lo,hi-5) if b[i]==0xE8 and call_target(b,i)==target]
def rel32_target(b,site,op=0xE9):
    if b[site]!=op:return None
    return site+5+int.from_bytes(b[site+1:site+5],'little',signed=True)
def jcc32_target(b,site):
    if b[site]!=0x0F or not 0x80<=b[site+1]<=0x8F:return None
    return site+6+int.from_bytes(b[site+2:site+6],'little',signed=True)

def fixup_records(raw):
    le=raw[LE_OFFSET:]; pages=u32(le,0x14); fp=u32(le,0x68); fr=u32(le,0x6C)
    pt=[u32(le,fp+4*i) for i in range(pages+1)]; out=[]
    for page in range(pages):
        i,end=fr+pt[page],fr+pt[page+1]
        while i<end:
            recstart=i; src,fl=le[i],le[i+1]; i+=2; listed=bool(src&0x20); st=src&0x0F; tt=fl&3
            if listed: count=le[i]; i+=1; srcs=[]
            else: count=1; srcs=[u16(le,i)]; i+=2
            obj=off=None
            if tt==0:
                obj=u16(le,i) if fl&0x40 else le[i]; i+=2 if fl&0x40 else 1
                if st!=2:
                    off=u32(le,i) if fl&0x10 else u16(le,i); i+=4 if fl&0x10 else 2
            elif tt in (1,2):
                i+=2 if fl&0x40 else 1
                i+=1 if tt==1 and fl&0x80 else (4 if fl&0x10 else 2)
            else:
                i+=2 if fl&0x40 else 1
            if fl&4:i+=4 if fl&0x20 else 2
            if listed:
                srcs=[u16(le,i+2*k) for k in range(count)]; i+=2*count
            if i>end: raise SystemExit(f'fixup parse overflow page {page}')
            for so in srcs:
                out.append({'page':page,'source_offset':so,'source_type':src,'flags':fl,'target_type':tt,'object':obj,'target_offset':off,'record_offset':recstart})
    return out

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--exe',required=True); ap.add_argument('--out'); a=ap.parse_args()
    raw=Path(a.exe).read_bytes(); o1=build_objects(raw)[0]['virtual']; fx=fixup_records(raw)
    cb=[]
    for r in fx:
        if r['target_type']==0 and r['object']==1 and r['target_offset'] is not None:
            source_actual=r['page']*0x1000+r['source_offset']-BIAS
            target_actual=r['target_offset']-BIAS
            if source_actual==0x106FD and target_actual==0x103D4:
                cb.append(r)
    checks={
      'exe_hash':hashlib.sha256(raw).hexdigest()==EXPECTED,
      'fixup_parse_complete':len(fx)==28547,
      'frame_callback_fixup_exact':len(cb)==1 and cb[0]['target_offset']==0x12E7C,
      'registration_immediate':o1[0x106FC:0x10701]==bytes.fromhex('ba 7c 2e 01 00'),
      'registration_calls_generic_registry':call_target(o1,0x10708)==0x30A68,
      'registry_type_770c':o1[0x30A71:0x30A76]==bytes.fromhex('bb 0c 77 00 00'),
      'registry_appends_callback':o1[0x30AB0:0x30AD5]==bytes.fromhex('8b 04 24 8b 90 80 02 00 00 8b 80 84 02 00 00 89 34 d0 8b 04 24 8b 90 80 02 00 00 8b 80 84 02 00 00 89 4c d0 04'),
      'invoker_reads_count':o1[0x3E5D3:0x3E5D9]==bytes.fromhex('8b 88 80 02 00 00'),
      'invoker_reads_array':o1[0x3E5E8:0x3E5EE]==bytes.fromhex('8b bb 84 02 00 00'),
      'invoker_loads_user_then_indirect_calls':o1[0x3E5F1:0x3E5F9]==bytes.fromhex('8b 54 39 04 46 ff 14 39'),
      'wrapper_type_770c':o1[0x44B5D:0x44B62]==bytes.fromhex('bb 0c 77 00 00'),
      'wrapper_calls_invoker':call_target(o1,0x44B79)==0x3E5C4,
      'scene_update_enumerates_770c':call_target(o1,0x2ABBB)==0x30DB8,
      'scene_update_calls_wrapper':call_target(o1,0x2ABE2)==0x44B58,
      'normal_gameplay_scene_update_call':call_target(o1,0x15EE)==0x2ABA8,
      'normal_gameplay_scene_update_gate_a':o1[0x15B1:0x15BF]==bytes.fromhex('66 83 3d 9a 1d 01 00 00 0f 85 34 00 00 00'),
      'normal_gameplay_scene_update_gate_b':o1[0x15BF:0x15C9]==bytes.fromhex('66 83 3d 24 1d 01 00 00 75 2a'),
      'outer_loop_backedge':jcc32_target(o1,0x346F)==0xFBB,
      'normal_path_world_timer_before_scene_update':call_target(o1,0x15AC)==0x1A848 and 0x15AC<0x15EE,
      'no_direct_ail_delay_from_outer_loop':calls(o1,0x37843,0xFBB,0x3475)==[],
    }
    bad=[k for k,v in checks.items() if not v]
    out={
      'schema':'openazrael.kg001.source_update_dispatch_validation','version':197,
      'status':'PASS' if not bad else 'FAIL','checks':checks,'failed':bad,
      'fixup_records':len(fx),
      'frame_callback':{
        'registered_function':'object1:0x103D4','registration_function':'object1:0x106E4',
        'fixup_source_actual':'0x106FD','fixup_target_encoded':'0x12E7C','le_bias':'0x2AA8',
        'registry':'object1:0x30A68','invoker':'object1:0x3E5C4','wrapper':'object1:0x44B58','scene_update':'object1:0x2ABA8',
        'normal_gameplay_call_site':'object1:0x15EE','outer_loop_backedge':'object1:0x346F -> 0xFBB'
      },
      'conclusion':{
        'reachability':'EXECUTABLE_CODE_VERIFIED',
        'source_update_event':'REGISTERED_SCENE_CALLBACK_DISPATCH_ON_ELIGIBLE_GAMEPLAY_UPDATE_PASS',
        'fixed_source_hz':None,
        'wall_clock_pacing':'HOLD_NOT_PROVEN',
        'production_policy':'DO_NOT_MAP_TO_GODOT_PROCESS_OR_PHYSICS_RATE_AS_SOURCE_EXACT_WITHOUT_PACING_PROOF'
      }
    }
    if a.out:Path(a.out).write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps(out,indent=2,sort_keys=True));return 1 if bad else 0
if __name__=='__main__':sys.exit(main())
