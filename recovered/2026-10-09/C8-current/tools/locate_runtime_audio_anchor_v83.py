#!/usr/bin/env python3
import argparse, hashlib, json, struct, subprocess, sys
from pathlib import Path
SIG=bytes.fromhex('53 51 52 56 57 C8 30 00 00 50 C7 45 F0 01 00 00')
OFF_CDE1=0xCDE1
OFF={'spatial_core':0xCDE1,'listener_position':0x227D0,'listener_forward':0x227DC,'emitter_table':0x227E8,'audio_manager_global':0x41D9C}

def iv(s): return int(s,0)
def find_all(buf, needle):
    out=[]; p=0
    while True:
        p=buf.find(needle,p)
        if p<0:return out
        out.append(p);p+=1

def main():
    ap=argparse.ArgumentParser(description='Locate the OpenAzrael v83 CDE1 audio anchor in a flat DOS memory dump and derive read-only capture addresses.')
    ap.add_argument('--memory-dump',required=True)
    ap.add_argument('--dump-base',type=iv,default=0,help='linear address represented by byte 0 of the dump (default 0)')
    ap.add_argument('--out-dir',required=True)
    ap.add_argument('--emit-kit',action='store_true',help='also invoke the v81 kit builder from the same tools directory')
    a=ap.parse_args(); p=Path(a.memory_dump); buf=p.read_bytes(); out=Path(a.out_dir); out.mkdir(parents=True,exist_ok=True)
    hs=find_all(buf,SIG)
    result={'schema':'openazrael.runtime_anchor_locator','version':83,'memory_dump':str(p),'memory_dump_sha256':hashlib.sha256(buf).hexdigest(),'dump_bytes':len(buf),'dump_base':hex(a.dump_base),'signature_hex':SIG.hex(),'hits':[],'status':None}
    for h in hs:
        rt=a.dump_base+h; delta=rt-OFF_CDE1
        derived={k:delta+v for k,v in OFF.items()}
        before=buf[max(0,h-16):h].hex(); after=buf[h+len(SIG):min(len(buf),h+len(SIG)+16)].hex()
        result['hits'].append({'dump_offset':hex(h),'runtime_cde1':hex(rt),'object1_delta':hex(delta),'derived':{k:hex(v) for k,v in derived.items()},'context_before_hex':before,'context_after_hex':after})
    if len(hs)==1:
        result['status']='UNIQUE_SIGNATURE_HIT'
        result['evidence_status']='OBSERVED_CANDIDATE_REQUIRES_CONTEXT_CONFIRMATION'
    elif len(hs)==0:
        result['status']='NO_SIGNATURE_HIT'; result['evidence_status']='NOT_OBSERVED'
    else:
        result['status']='AMBIGUOUS_SIGNATURE_HITS'; result['evidence_status']='NOT_EVIDENCE_READY'
    (out/'runtime_anchor_v83.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    if a.emit_kit and len(hs)==1:
        builder=Path(__file__).with_name('build_dosbox_capture_kit_v81.py')
        kit=out/'capture_kit'
        subprocess.run([sys.executable,str(builder),'--runtime-cde1',hex(a.dump_base+hs[0]),'--out-dir',str(kit)],check=True)
    print(json.dumps({'status':result['status'],'hits':len(hs),'runtime_cde1':result['hits'][0]['runtime_cde1'] if len(hs)==1 else None,'out_dir':str(out)},indent=2))
    return 0 if len(hs)==1 else 2
if __name__=='__main__': raise SystemExit(main())
