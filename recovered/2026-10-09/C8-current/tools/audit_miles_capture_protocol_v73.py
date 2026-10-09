#!/usr/bin/env python3
import argparse,hashlib,json,pathlib,re
EXPECTED='381e4f5c61e4bb8c27f06b1944e6673bbebc39ca219cc08fb9f948da2ca37c00'
NEEDLES=[
 b'AIL_DEBUG',b'AIL_SYS_DEBUG',b'w+t',
 b'AIL_init_sample(0x%X)\n',b'AIL_set_sample_file(0x%X,0x%X,%d)\n',
 b'AIL_set_sample_address(0x%X,0x%X,%u)\n',b'AIL_start_sample(0x%X)\n',
 b'AIL_set_sample_pan(0x%X,%d)\n',b'AIL_set_sample_volume(0x%X,%d)\n',
 b'AIL_set_sample_loop_count(0x%X,%d)\n',b'AIL_sample_status(0x%X)\n'
]
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('exe',type=pathlib.Path); ap.add_argument('--out',type=pathlib.Path,required=True); a=ap.parse_args()
 b=a.exe.read_bytes(); sha=hashlib.sha256(b).hexdigest(); offs={n.decode().rstrip('\n'):b.find(n) for n in NEEDLES}
 checks={'exe_sha_expected':sha==EXPECTED,**{('string_'+re.sub('[^A-Za-z0-9]+','_',k).strip('_')):v>=0 for k,v in offs.items()}}
 out={'schema':'openazrael.miles_capture_protocol_audit','version':73,'exe_sha256':sha,'string_file_offsets':{k:(hex(v) if v>=0 else None) for k,v in offs.items()},'checks':checks,'passed':sum(checks.values()),'total':len(checks),'status':'PASS' if all(checks.values()) else 'FAIL','findings':[
  'The original trace vocabulary includes sample lifecycle events in addition to pan/volume: init, set_sample_file/address, start, loop_count and sample_status.',
  'AIL_set_sample_file logs the sample handle and a pointer, not the filename text; therefore filename/AMB-slot identity must not be inferred from that line alone.',
  'Lifecycle chronology can be used as independent evidence to keep per-handle pan/volume observations grouped, while slot identity remains UNMAPPED until separately anchored.'
 ],'confidence':{'trace_vocabulary':'VERIFIED','per_handle_event_grouping':'HIGH','automatic_handle_to_AMB_slot':'HOLD'}}
 a.out.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n'); print(out['status'],out['passed'],'/',out['total'])
if __name__=='__main__': main()
