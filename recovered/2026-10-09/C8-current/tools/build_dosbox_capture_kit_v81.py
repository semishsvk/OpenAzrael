#!/usr/bin/env python3
import argparse,json
from pathlib import Path
OFF={'spatial_core':0xCDE1,'listener_position':0x227D0,'listener_forward':0x227DC,'emitter_table':0x227E8,'audio_manager_global':0x41D9C}
def iv(s): return int(s,0)
def main():
 ap=argparse.ArgumentParser(description='Build a debugger-agnostic, read-only OpenAzrael v81 original-runtime capture kit.')
 ap.add_argument('--runtime-cde1',required=True,type=iv)
 ap.add_argument('--manager-pointer',type=iv)
 ap.add_argument('--out-dir',required=True)
 a=ap.parse_args(); out=Path(a.out_dir); out.mkdir(parents=True,exist_ok=True)
 base=a.runtime_cde1-OFF['spatial_core']; rt={k:base+v for k,v in OFF.items()}
 reads=[('listener_pos.bin',rt['listener_position'],12),('listener_fwd.bin',rt['listener_forward'],12),('emitters.bin',rt['emitter_table'],168),('audio_manager_pointer.bin',rt['audio_manager_global'],4)]
 if a.manager_pointer is not None: reads.append(('manager.bin',a.manager_pointer,0x364))
 manifest={'schema':'openazrael.dosbox_capture_kit','version':81,'mode':'READ_ONLY','anchor':{'runtime_cde1':hex(a.runtime_cde1),'object1_delta':hex(base),'confidence':'OBSERVED_DERIVED'},'manager_pointer':hex(a.manager_pointer) if a.manager_pointer is not None else None,'reads':[{'file':f,'address':hex(addr),'bytes':n} for f,addr,n in reads], 'required_external_files':['AIL_DEBUG.LOG','openazrael_audio_capture_v71.jsonl'],'evidence_rules':['Do not patch R.EXE.','Capture listener/emitter/manager memory from one paused original-game state.','Bound the AIL_DEBUG interval that corresponds to that state.','Do not infer Miles-handle identity from log order.','A synthetic test is never original-runtime evidence.']}
 (out/'capture_manifest_v81.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
 lines=['OpenAzrael v81 original-runtime capture kit','',f'Observed spatial-core anchor: {a.runtime_cde1:#x}',f'Object-1 runtime delta: {base:#x}','','Pause the original game at the pose you want to test and dump these ranges without modifying memory:']
 for f,addr,n in reads: lines.append(f'  {f:28s} address={addr:#x} bytes={n} (0x{n:X})')
 if a.manager_pointer is None: lines += ['','First dump audio_manager_pointer.bin, decode its little-endian 32-bit pointer, then rebuild this kit with --manager-pointer 0xVALUE to obtain manager.bin address.']
 lines += ['','Also preserve the matching AIL_DEBUG.LOG and an OpenAzrael F9 capture for the same room/pose. Record the inclusive AIL log start/end line numbers.','', 'The kit is debugger-agnostic on purpose: command syntax differs between DOSBox-X/debug builds. The addresses and byte counts above are the evidence; do not substitute guessed addresses.']
 (out/'CAPTURE_STEPS.txt').write_text('\n'.join(lines)+'\n')
 print(json.dumps({'status':'PASS','out_dir':str(out),'reads':len(reads),'manager_ready':a.manager_pointer is not None},indent=2))
if __name__=='__main__': main()
