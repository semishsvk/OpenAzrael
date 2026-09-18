#!/usr/bin/env python3
import argparse, hashlib, json, struct, subprocess, sys
from pathlib import Path
SIG=bytes.fromhex('53 51 52 56 57 C8 30 00 00 50 C7 45 F0 01 00 00')
OFF_CDE1=0xCDE1
OFF={'listener_position':0x227D0,'listener_forward':0x227DC,'emitter_table':0x227E8,'audio_manager_global':0x41D9C}

def iv(s): return int(s,0)
def hits(buf,needle):
 out=[]; p=0
 while True:
  p=buf.find(needle,p)
  if p<0:return out
  out.append(p); p+=1

def slice_linear(buf,dump_base,address,size,label):
 o=address-dump_base
 if o<0 or o+size>len(buf):
  raise ValueError(f'{label}: runtime range {address:#x}..{address+size:#x} is outside dump {dump_base:#x}..{dump_base+len(buf):#x}')
 return buf[o:o+size]

def main():
 ap=argparse.ArgumentParser(description='OpenAzrael v84 one-command read-only memory-dump to pose-verified Classic audio parity pipeline.')
 ap.add_argument('--memory-dump',required=True); ap.add_argument('--dump-base',type=iv,default=0)
 ap.add_argument('--miles-log',required=True); ap.add_argument('--reference-capture',required=True); ap.add_argument('--room-id',required=True)
 ap.add_argument('--trace-start-line',required=True,type=int); ap.add_argument('--trace-end-line',required=True,type=int)
 ap.add_argument('--out-dir',required=True); ap.add_argument('--position-tolerance',type=float,default=0.05); ap.add_argument('--forward-tolerance',type=float,default=0.002)
 a=ap.parse_args(); p=Path(a.memory_dump); buf=p.read_bytes(); out=Path(a.out_dir); out.mkdir(parents=True,exist_ok=True)
 hs=hits(buf,SIG)
 manifest={'schema':'openazrael.memory_audio_capture_pipeline','version':84,'memory_dump':str(p),'memory_dump_sha256':hashlib.sha256(buf).hexdigest(),'dump_base':hex(a.dump_base),'dump_bytes':len(buf),'signature_hits':len(hs),'status':'NOT_EVIDENCE_READY','blockers':[]}
 if len(hs)!=1:
  manifest['blockers'].append('NO_UNIQUE_CDE1_SIGNATURE')
  (out/'pipeline_v84.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n'); print(json.dumps(manifest,indent=2)); return 2
 runtime_cde1=a.dump_base+hs[0]; delta=runtime_cde1-OFF_CDE1
 rt={k:delta+v for k,v in OFF.items()}; manifest['runtime_cde1']=hex(runtime_cde1); manifest['object1_delta']=hex(delta); manifest['derived_addresses']={k:hex(v) for k,v in rt.items()}
 try:
  lp=slice_linear(buf,a.dump_base,rt['listener_position'],12,'listener_position')
  lf=slice_linear(buf,a.dump_base,rt['listener_forward'],12,'listener_forward')
  em=slice_linear(buf,a.dump_base,rt['emitter_table'],168,'emitter_table')
  gp=slice_linear(buf,a.dump_base,rt['audio_manager_global'],4,'audio_manager_global')
  manager_ptr=struct.unpack('<I',gp)[0]; manifest['audio_manager_pointer']=hex(manager_ptr)
  mg=slice_linear(buf,a.dump_base,manager_ptr,0x364,'audio_manager')
 except ValueError as e:
  manifest['blockers'].append('MEMORY_RANGE_OUTSIDE_DUMP'); manifest['detail']=str(e)
  (out/'pipeline_v84.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n'); print(json.dumps(manifest,indent=2)); return 2
 files={'listener_pos.bin':lp,'listener_fwd.bin':lf,'emitters.bin':em,'audio_manager_pointer.bin':gp,'manager.bin':mg}
 hashes={}
 for n,b in files.items():
  (out/n).write_bytes(b); hashes[n]={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
 manifest['extracted']=hashes
 proc=Path(__file__).with_name('process_pose_verified_audio_capture_v80.py'); parity=out/'parity_v84.json'
 cmd=[sys.executable,str(proc),'--manager',str(out/'manager.bin'),'--emitters',str(out/'emitters.bin'),'--listener-position',str(out/'listener_pos.bin'),'--listener-forward',str(out/'listener_fwd.bin'),'--miles-log',a.miles_log,'--reference-capture',a.reference_capture,'--room-id',a.room_id,'--trace-start-line',str(a.trace_start_line),'--trace-end-line',str(a.trace_end_line),'--position-tolerance',str(a.position_tolerance),'--forward-tolerance',str(a.forward_tolerance),'--out',str(parity)]
 cp=subprocess.run(cmd,text=True,capture_output=True)
 manifest['parity_tool_returncode']=cp.returncode; manifest['parity_tool_stdout']=cp.stdout.strip(); manifest['parity_tool_stderr']=cp.stderr.strip()
 if parity.exists():
  pr=json.loads(parity.read_text()); manifest['parity_status']=pr.get('status'); manifest['parity_summary']={k:pr.get(k) for k in ('comparable_cases','exact_matches','failures','evidence_blockers')}; manifest['status']=pr.get('status','NOT_EVIDENCE_READY')
 else:
  manifest['blockers'].append('PARITY_PROCESSOR_DID_NOT_EMIT_RESULT')
 (out/'pipeline_v84.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
 print(json.dumps({'status':manifest['status'],'runtime_cde1':hex(runtime_cde1),'manager_pointer':hex(manager_ptr),'parity_status':manifest.get('parity_status'),'out_dir':str(out)},indent=2))
 return 1 if manifest['status']=='FAIL' else (0 if manifest['status']=='PASS' else 2)
if __name__=='__main__': raise SystemExit(main())
