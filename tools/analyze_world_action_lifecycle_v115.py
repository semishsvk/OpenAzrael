#!/usr/bin/env python3
from pathlib import Path
import argparse, hashlib, json, sys

EXPECTED_EXE='381e4f5c61e4bb8c27f06b1944e6673bbebc39ca219cc08fb9f948da2ca37c00'
ALLOC=0x20C00
INSERT27=0x295B0
INSERT37=0x295F4
READER27_INSERT_CALL=0x296EC
READER37_INSERT_CALL=0x2968A
READER27_ALLOC_MOV=0x29703
READER27_ALLOC_CALL=0x29712
CONDITION_RECORD_SCAN=0x2990C
CONDITION_RECORD_SCAN_CALL=0x29DDF
PENDING_GROUP_COUNT=0x438B0
PENDING_GROUP_ARRAY=0x438B4
DISPATCH=0x18698
SOUND_HANDLER=0x191E9

def sha(b): return hashlib.sha256(b).hexdigest()
def call_target(buf,site):
    if site<0 or site+5>len(buf) or buf[site]!=0xE8: return None
    return site+5+int.from_bytes(buf[site+1:site+5],'little',signed=True)
def refs(buf,target): return [i for i in range(len(buf)-4) if buf[i]==0xE8 and call_target(buf,i)==target]

def immediate_27_allocs(o1):
    out=[]
    for i in range(len(o1)-20):
        if o1[i:i+5]!=b'\xb8\x1b\x00\x00\x00': continue
        for j in range(i+5,min(i+25,len(o1)-4)):
            if o1[j]==0xE8 and call_target(o1,j)==ALLOC: out.append((i,j))
    return out

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--exe',required=True); ap.add_argument('--out',required=True); a=ap.parse_args()
    sys.path.insert(0,str(Path(__file__).resolve().parent))
    from audit_file_open_families_v103 import build_objects
    exe=Path(a.exe).read_bytes(); o1=build_objects(exe)[0]['virtual']
    a27=immediate_27_allocs(o1)
    checks={
      'exe_hash':sha(exe)==EXPECTED_EXE,
      'insert27_only_direct_caller_is_reader':refs(o1,INSERT27)==[READER27_INSERT_CALL],
      'insert37_only_direct_caller_is_reader':refs(o1,INSERT37)==[READER37_INSERT_CALL],
      'reader27_insert_edge':call_target(o1,READER27_INSERT_CALL)==INSERT27,
      'reader37_insert_edge':call_target(o1,READER37_INSERT_CALL)==INSERT37,
      'only_immediate_27_alloc_is_reader':a27==[(READER27_ALLOC_MOV,READER27_ALLOC_CALL)],
      'condition_record_scan_single_direct_caller':refs(o1,CONDITION_RECORD_SCAN)==[CONDITION_RECORD_SCAN_CALL],
      'condition_scan_reads_second_list_count':o1[0x29c47:0x29c4e]==bytes.fromhex('668b5506668910'),
      'condition_scan_reads_second_list_pointer':o1[0x29c4e:0x29c54]==bytes.fromhex('8b5508895002'),
      'pending_group_count_load':o1[0x29987:0x2998e]==bytes.fromhex('668b35b0380400'),
      'pending_group_count_store':o1[0x29991:0x2999b]==bytes.fromhex('6689f0668935b0380400'),
      'pending_group_entry_size_six':o1[0x29c0a:0x29c1b]==bytes.fromhex('31d26689f28d04950000000029d08d1400'),
      'pending_group_array_global_load':o1[0x29c1b:0x29c25]==bytes.fromhex('a1b4380400e84367ffff'),
      'pending_group_array_global_store':o1[0x29c25:0x29c2a]==bytes.fromhex('a3b4380400'),
      'dispatcher_reads_pending_count':o1[0x186a3:0x186ac]==bytes.fromhex('31d2668b0db0380400'),
      'dispatcher_entry_stride_six':o1[0x186e3:0x186f2]==bytes.fromhex('31c0668b45f86bc0068b15b4380400'),
      'dispatcher_reads_group_count':o1[0x186f4:0x186fc]==bytes.fromhex('8b55f4663b1073c6'),
      'dispatcher_reads_original_pointer_array':o1[0x186fc:0x18708]==bytes.fromhex('31d28b4002668b55f48b0490'),
      'dispatcher_dispatches_original_record_pointer':o1[0x18708:0x18715]==bytes.fromhex('8945e88a003c280f871b0c0000'),
      'sound_handler_has_no_record_store_before_pointer_repurpose':o1[SOUND_HANDLER:0x19208]==bytes.fromhex('a1883804008b55e8668b00663b420f0f85e2f4ffff668b420d8b1590380400'),
    }
    bad=[k for k,v in checks.items() if not v]
    if bad: raise SystemExit('v115 invariant failure: '+', '.join(bad))
    out={
      'schema':'openazrael.world_action_record_lifecycle_audit','version':115,'status':'PASS',
      'sources':{'r_exe_sha256':sha(exe)},
      'population_path':{
        'record27_insert_function_hex':hex(INSERT27),'direct_call_sites':[hex(x) for x in refs(o1,INSERT27)],
        'record37_insert_function_hex':hex(INSERT37),'direct_call_sites_37':[hex(x) for x in refs(o1,INSERT37)],
        'immediate_27_alloc_matches':[{'mov_site_hex':hex(x),'call_site_hex':hex(y)} for x,y in a27],
        'finding':'In the audited direct-call/immediate-allocation classes, the WORLD reader is the only population path for the nested 27-byte and 37-byte pointer lists and the only direct malloc(27)-style allocation.',
        'boundary':'Does not exclude indirect calls, generic/variable-size allocators, stack/static construction, or external authoring code.'
      },
      'shallow_runtime_schedule':{
        'condition_scan_hex':hex(CONDITION_RECORD_SCAN),'condition_scan_direct_call_hex':hex(CONDITION_RECORD_SCAN_CALL),
        'pending_group_count_global_hex':hex(PENDING_GROUP_COUNT),'pending_group_array_global_hex':hex(PENDING_GROUP_ARRAY),'entry_size':6,
        'entry_layout':{'count27':{'offset':0,'size':2,'source':'nested object +6'},'pointer_array27':{'offset':2,'size':4,'source':'nested object +8'}},
        'finding':'On condition success, runtime scheduling stores only the original 27-byte-list count and pointer-array address in a 6-byte pending group. It does not copy the 27-byte records.',
        'confidence':'VERIFIED'
      },
      'dispatch_path':{
        'dispatcher_hex':hex(DISPATCH),'pending_group_stride':6,
        'finding':'The dispatcher iterates the 6-byte pending groups, follows the original pointer array, obtains the original 27-byte record pointer, reads its opcode and dispatches it in place.',
        'sound_handler_hex':hex(SOUND_HANDLER),'sound_handler_mutates_record':False,
        'confidence':'VERIFIED for audited control/data flow'
      },
      'lifecycle_conclusion':{
        'finding':'For the bound runtime path, 27-byte action records are loaded from WORLD, retained by pointer, shallow-scheduled by count+pointer-array reference, and dispatched in place. No copy/normalization step is present between WORLD deserialization and opcode execution in this path.',
        'tail_implication':'The varying +17..+26 bytes observed in v114 are already present in serialized WORLD and survive unchanged into dispatch. Their exact authoring origin remains upstream/HOLD; the audited runtime path does not manufacture them.',
        'producer_boundary':'The complete PUZZLES/ROOMS -> WORLD producer/compiler remains HOLD.'
      },
      'next_target':'Audit static construction/mutation patterns outside the load/schedule/dispatch path: generic copies of 27 bytes, stores to +17..+26 near action-building code, and any indirect reachability into the paired WORLD writer.',
      'checks':checks
    }
    Path(a.out).write_text(json.dumps(out,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps({'status':'PASS','checks':len(checks),'insert27_callers':len(refs(o1,INSERT27)),'insert37_callers':len(refs(o1,INSERT37)),'immediate_27_allocs':len(a27)},indent=2))
if __name__=='__main__': main()
