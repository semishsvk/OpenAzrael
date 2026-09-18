#!/usr/bin/env python3
import argparse,json
from pathlib import Path
OFF={'spatial_core':0xCDE1,'listener_position':0x227D0,'listener_forward':0x227DC,'emitter_table':0x227E8,'audio_manager_global':0x41D9C}
def iv(s): return int(s,0)
def main():
 ap=argparse.ArgumentParser(description='Build a v78 runtime capture plan from one observed R.EXE spatial-core address.')
 ap.add_argument('--runtime-cde1',required=True,type=iv,help='Observed linear runtime address of object1+0xCDE1')
 ap.add_argument('--manager-pointer',type=iv,help='Optional pointer value read from resolved audio_manager_global')
 ap.add_argument('--out',required=True)
 a=ap.parse_args(); base=a.runtime_cde1-OFF['spatial_core']
 rt={k:base+v for k,v in OFF.items()}
 out={'schema':'openazrael.runtime_capture_plan','version':78,'status':'READY','anchor':{'object1_offset':'0xCDE1','runtime_address':hex(a.runtime_cde1)},'object1_runtime_delta':hex(base),'resolved_runtime_addresses':{k:hex(v) for k,v in rt.items()},'reads':[{'name':'listener_position','address':hex(rt['listener_position']),'bytes':12},{'name':'listener_forward','address':hex(rt['listener_forward']),'bytes':12},{'name':'emitters','address':hex(rt['emitter_table']),'bytes':168},{'name':'audio_manager_pointer','address':hex(rt['audio_manager_global']),'bytes':4}], 'manager':{'pointer':hex(a.manager_pointer) if a.manager_pointer is not None else None,'dump_bytes':0x364,'status':'READY' if a.manager_pointer is not None else 'NEEDS_POINTER_READ'},'confidence':{'same_object_address_resolution':'HIGH','absolute_addresses':'OBSERVED_DERIVED','manager_pointer':'OBSERVED' if a.manager_pointer is not None else 'UNOBSERVED'},'safety':'No R.EXE patching; read-only runtime observation.'}
 Path(a.out).write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
 print(json.dumps({'status':'PASS','delta':hex(base),'emitter_table':hex(rt['emitter_table']),'audio_manager_global':hex(rt['audio_manager_global']),'manager':out['manager']['status']},indent=2))
if __name__=='__main__': main()
