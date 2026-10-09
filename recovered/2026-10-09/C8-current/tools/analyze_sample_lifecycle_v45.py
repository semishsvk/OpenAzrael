#!/usr/bin/env python3
import argparse, hashlib, json, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from analyze_ambient_loader_v42 import build_obj1, EXPECTED

def rel32(b, at):
    return at+5+int.from_bytes(b[at+1:at+5],'little',signed=True)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('exe'); ap.add_argument('--out',required=True); a=ap.parse_args()
    raw=Path(a.exe).read_bytes(); b=build_obj1(raw); sha=hashlib.sha256(raw).hexdigest()
    checks={
      'exe_hash': sha==EXPECTED,
      'resource_lookup_2bc74': rel32(b,0x1feba)==0x2bc74,
      'resource_alloc_size_11': b[0x1fed6:0x1fee0]==bytes.fromhex('b80b000000e8200d0000'),
      'resource_ctor_1e9d4': rel32(b,0x1fef2)==0x1e9d4,
      'resource_name_assign_1ea0a': rel32(b,0x1ff14)==0x1ea0a,
      'resource_cache_insert_2b8d4': rel32(b,0x1ff2f)==0x2b8d4,
      'resource_load_97b7': rel32(b,0x1ff3a)==0x97b7,
      'sample_status_free_scan': rel32(b,0x1ee7b)==0x38f64,
      'sample_init_stop_then_init': rel32(b,0x1efe5)==0x38c45 and rel32(b,0x1eff0)==0x38961,
      'type2_set_address': rel32(b,0x1f02b)==0x38ad4,
      'type1_set_file': rel32(b,0x1f04e)==0x389ce,
      'apply_runtime_params': rel32(b,0x1f088)==0x20288,
      'set_loop_count': rel32(b,0x1f097)==0x38eee,
      'start_sample': rel32(b,0x1f0a2)==0x38bd8,
      'runtime_pan': rel32(b,0x2031f)==0x38e78,
      'runtime_volume': rel32(b,0x20330)==0x38e02,
      'sample_handle_stride_36': b[0x1ee66:0x1ee72]==bytes.fromhex('8b45e2c1f8106bc0240345f0'),
    }
    bad=[k for k,v in checks.items() if not v]
    if bad: raise SystemExit('v45 invariant failed: '+repr(bad))
    # Backend identities: consecutive Miles diagnostics/order independently anchors these wrappers.
    backend={
      '0x38961':'AIL_init_sample', '0x389CE':'AIL_set_sample_file', '0x38AD4':'AIL_set_sample_address',
      '0x38BD8':'AIL_start_sample', '0x38C45':'AIL_stop_sample', '0x38E02':'AIL_set_sample_volume',
      '0x38E78':'AIL_set_sample_pan', '0x38EEE':'AIL_set_sample_loop_count', '0x38F64':'AIL_sample_status'
    }
    out={
      'schema':'openazrael.sample_lifecycle','version':45,'status':'PASS','exe_sha256':sha,'invariants':checks,
      'backend_identity':{'mapping':backend,'confidence':'HIGH','basis':'Contiguous backend wrapper ordering and diagnostic slots match the literal Miles AIL sample API diagnostic sequence; volume/pan were independently anchored in v38.'},
      'resource_resolution':{
        'routine':'0x1FE7F','confidence':'HIGH',
        'behavior':['lookup filename in manager/cache at owner+0x1A8 via 0x2BC74','on cache miss allocate 11-byte resource wrapper and construct it','assign filename via 0x1EA0A','insert resource into cache via 0x2B8D4','load/resolve payload via 0x97B7','return cached/new descriptor'],
        'exact_resource_class_name':'HOLD'
      },
      'sample_start':{
        'routine':'0x1EDD7','confidence':'HIGH',
        'behavior':['validate manager and descriptor','select/free a sample slot using AIL_sample_status','stop and initialize the selected Miles sample','bind payload using AIL_set_sample_address for descriptor type 2 or AIL_set_sample_file for type 1','apply per-slot runtime parameters via 0x20288','set loop count','start sample','store descriptor pointer in slot+0x20'],
        'slot_stride_bytes':36
      },
      'runtime_parameter_apply':{
        'routine':'0x20288','confidence':'HIGH',
        'confirmed':['calls AIL_set_sample_pan from slot parameter +0x08','calls AIL_set_sample_volume from slot parameter +0x18'],
        'additional_call':'0x3974F using slot parameter +0x04; exact Miles identity HOLD'
      },
      'classic_audio_impact':{
        'sample_lifecycle':'HIGH','loop_count_is_explicitly_set_before_start':'HIGH','sample_status_controls_reuse':'HIGH',
        'exact_loop_value_for_AMB':'HOLD','exact_playback_rate':'HOLD','exact_attenuation_formula':'HOLD','exact_pan_formula':'HOLD'
      },
      'next':['Trace AMB call arguments into 0x1EF44/0x1EDD7 to recover the exact loop-count value used by room ambience.','Identify backend 0x3974F and the slot +0x04 parameter to determine playback-rate/default parameter behavior.','Then implement these confirmed lifecycle semantics in Classic Audio without inventing unresolved numeric constants.']
    }
    Path(a.out).write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'status':'PASS','checks':len(checks),'sample_lifecycle':'HIGH','resource_resolution':'HIGH'},indent=2))
if __name__=='__main__': main()
