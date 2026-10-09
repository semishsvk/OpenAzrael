#!/usr/bin/env python3
import argparse,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from analyze_ambient_loader_v42 import build_obj1,EXPECTED

def rel32(b,at): return at+5+int.from_bytes(b[at+1:at+5],'little',signed=True)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('exe');ap.add_argument('--out',required=True);a=ap.parse_args()
 raw=Path(a.exe).read_bytes();b=build_obj1(raw);sha=hashlib.sha256(raw).hexdigest()
 checks={
 'exe_hash':sha==EXPECTED,
 'record_seed_22050':b[0x202d2:0x202d9]==bytes.fromhex('c745e022560000'),
 'record_seed_property0':b[0x202ea:0x202f1]==bytes.fromhex('c745d400000000'),
 'builder_property_to_plus04':b[0x20240:0x20249]==bytes.fromhex('8b45f48b55ec894204'),
 'builder_pan_to_plus08':b[0x20249:0x20252]==bytes.fromhex('8b45f88b55ec894208'),
 'builder_22050_to_plus0c':b[0x20252:0x2025b]==bytes.fromhex('8b45108b55ec89420c'),
 'apply_property_calls_3974f':rel32(b,0x2030e)==0x3974f,
 'runtime_property_update_calls_3974f':rel32(b,0x1fcc8)==0x3974f,
 'paired_getter_397c5':rel32(b,0x1fd20)==0x397c5,
 'pan_apply_is_separate':rel32(b,0x2031f)==0x38e78,
 'volume_apply_is_separate':rel32(b,0x20330)==0x38e02,
 'miles_rate_strings_present':b'AIL_set_sample_playback_rate(0x%X,%d)' in raw and b'AIL_sample_playback_rate(0x%X)' in raw,
 'miles_position_strings_present':b'AIL_set_sample_position(0x%X,%u)' in raw,
 }
 bad=[k for k,v in checks.items() if not v]
 if bad: raise SystemExit('v47 invariant failed: '+repr(bad))
 out={'schema':'openazrael.sample_rate_semantics','version':47,'status':'PASS','exe_sha256':sha,'invariants':checks,
 'finding':{
  'wrapper_0x3974F':{'identity':'AIL_set_sample_playback_rate','confidence':'HIGH','evidence':['two-argument setter wrapper used by the sample-pool property updater','immediately paired with 0x397C5 getter used on the same sample handle','the executable contains the matching Miles setter/getter diagnostics','pan and volume are independently bound to 0x38E78 and 0x38E02']},
  'wrapper_0x397C5':{'identity':'AIL_sample_playback_rate','confidence':'HIGH'},
  'sample_pool_layout':{'record_stride':36,'sample_handle_whole_record_offset':'0x04','playback_rate_whole_record_offset':'0x08','pan_whole_record_offset':'0x0C','seed_22050_whole_record_offset':'0x10','volume_whole_record_offset':'0x1C','confidence':'HIGH'},
  'initial_playback_rate_argument':{'value':0,'confidence':'HIGH','semantic_meaning':'HOLD','note':'The engine explicitly calls the playback-rate setter with numeric 0 during this initialization path. Do not reinterpret the separate 22050 field as the applied Miles playback rate without a proven dataflow.'},
  'literal_22050':{'value':22050,'confidence':'HIGH','semantic_role':'HOLD','note':'v47 corrects the tempting but unsupported interpretation that this literal is necessarily the applied playback rate. It is stored in a different field (+0x10 whole-record) from the field sent to AIL_set_sample_playback_rate (+0x08).'}
 },
 'impact':{'0x3974F_identity':'HIGH','numeric_initial_rate_argument_0':'HIGH','22050_literal_presence_and_field':'HIGH','meaning_of_rate_0':'HOLD','meaning_of_22050_field':'HOLD','exact_3d_attenuation':'HOLD','exact_3d_pan_formula':'HOLD'},
 'next':['Determine Miles 3.x semantics of AIL_set_sample_playback_rate(...,0) from executable behavior or contemporaneous SDK evidence.','Trace every read/write of sample-pool whole-record +0x10 to identify the 22050 field.','Continue exact attenuation/pan reconstruction after rate-field separation is locked.']}
 Path(a.out).write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
 print(json.dumps({'status':'PASS','checks':len(checks),'wrapper_0x3974F':'AIL_set_sample_playback_rate','initial_rate_argument':0,'literal_22050_role':'HOLD'},indent=2))
if __name__=='__main__':main()
