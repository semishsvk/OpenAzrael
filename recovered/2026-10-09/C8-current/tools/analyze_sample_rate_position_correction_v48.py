#!/usr/bin/env python3
import argparse,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from analyze_ambient_loader_v42 import build_obj1,EXPECTED

def rel32(b,at): return at+5+int.from_bytes(b[at+1:at+5],'little',signed=True)
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('exe'); ap.add_argument('--out',required=True); a=ap.parse_args()
 raw=Path(a.exe).read_bytes(); b=build_obj1(raw); sha=hashlib.sha256(raw).hexdigest()
 checks={
  'exe_hash':sha==EXPECTED,
  'seed_22050':b[0x202d2:0x202d9]==bytes.fromhex('c745e022560000'),
  'builder_22050_to_record_plus10':b[0x20252:0x2025b]==bytes.fromhex('8b45108b55ec89420c'),
  'dedicated_rate_setter_writes_plus10':b[0x1f4e9:0x1f4ef]==bytes.fromhex('8b45f4894210'),
  'dedicated_rate_setter_calls_38d8c':rel32(b,0x1f507)==0x38d8c,
  'initial_apply_reads_record_plus08':b[0x20305:0x2030b]==bytes.fromhex('8b45f0ff7004'),
  'initial_apply_plus08_calls_3974f':rel32(b,0x2030e)==0x3974f,
  'runtime_plus08_setter_calls_3974f':rel32(b,0x1fcc8)==0x3974f,
  'paired_397c5_getter_call':rel32(b,0x1fd20)==0x397c5,
  'volume_wrapper_38e02':rel32(b,0x20330)==0x38e02,
  'pan_wrapper_38e78':rel32(b,0x2031f)==0x38e78,
  'loop_wrapper_38eee':rel32(b,0x1f097)==0x38eee,
  'miles_rate_string':b'AIL_set_sample_playback_rate(0x%X,%d)' in raw,
  'miles_position_pair':b'AIL_set_sample_position(0x%X,%u)' in raw and b'AIL_sample_position(0x%X)' in raw,
 }
 bad=[k for k,v in checks.items() if not v]
 if bad: raise SystemExit('v48 invariant failed: '+repr(bad))
 out={
  'schema':'openazrael.sample_rate_position_correction','version':48,'status':'PASS','exe_sha256':sha,'invariants':checks,
  'correction':{
   'v47_status':'SUPERSEDED_FOR_WRAPPER_IDENTITY_AND_FIELD_LABELS',
   'wrapper_0x38D8C':{'identity':'AIL_set_sample_playback_rate','confidence':'HIGH','reason':'A dedicated engine setter writes the same per-sample record field at whole-record +0x10 and immediately invokes 0x38D8C on that record sample handle; the field is seeded with 22050. 0x38E02/0x38E78/0x38EEE remain the adjacent volume/pan/loop controls.'},
   'wrapper_0x3974F':{'identity':'AIL_set_sample_position','confidence':'HIGH','reason':'The +0x08 field has its own setter/getter path through 0x3974F/0x397C5, while playback rate has the separate proven +0x10 -> 0x38D8C path. The executable contains the matching Miles sample-position setter/getter pair.'},
   'wrapper_0x397C5':{'identity':'AIL_sample_position','confidence':'HIGH'},
   'sample_pool_layout':{
    'stride':36,'sample_handle_offset':'0x04','sample_position_offset':'0x08','pan_offset':'0x0C','playback_rate_offset':'0x10','volume_offset':'0x1C','confidence':'HIGH'
   },
   'initial_defaults':{'sample_position':0,'pan':64,'playback_rate':22050,'volume':64,'confidence':'HIGH'},
   'important_note':'v47 incorrectly labeled 0x3974F as playback-rate and therefore treated 22050 as unrelated. v48 corrects this: 22050 is the stored playback-rate field used by the dedicated rate setter; the zero field is sample position.'
  },
  'impact':{'classic_audio_default_playback_rate_22050':'HIGH','initial_sample_position_0':'HIGH','v47_rate_zero_semantics':'RETRACTED','exact_3d_attenuation':'HOLD','exact_3d_pan_formula':'HOLD'},
  'next':['Trace call sites of 0x1F4A5 to determine when/why playback rate changes from the 22050 default.','Resolve the remaining AMB literal 1000 dataflow.','Continue exact 3D attenuation and pan reconstruction.']
 }
 Path(a.out).write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
 print(json.dumps({'status':'PASS','checks':len(checks),'playback_rate_wrapper':'0x38D8C','position_wrapper':'0x3974F','default_playback_rate':22050},indent=2))
if __name__=='__main__': main()
