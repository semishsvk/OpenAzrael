#!/usr/bin/env python3
import argparse,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from analyze_ambient_loader_v42 import build_obj1,EXPECTED

def rel32(b,at): return at+5+int.from_bytes(b[at+1:at+5],'little',signed=True)
def calls_to(b,target):
 return [i for i in range(len(b)-5) if b[i]==0xE8 and rel32(b,i)==target]
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('exe'); ap.add_argument('--out',required=True); a=ap.parse_args()
 raw=Path(a.exe).read_bytes(); b=build_obj1(raw); sha=hashlib.sha256(raw).hexdigest()
 cs=calls_to(b,0x1f4a5)
 checks={
  'exe_hash':sha==EXPECTED,
  'exactly_three_direct_calls_to_rate_setter':cs==[0x5009,0xe552,0xe590],
  'caller_5009_loads_22050':b[0x5004:0x5009]==bytes.fromhex('bb22560000'),
  'caller_e552_loads_22050':b[0xe544:0xe552].endswith(bytes.fromhex('bb22560000a19c1d040031c931d2')),
  'caller_e590_loads_22050':b[0xe582:0xe590].startswith(bytes.fromhex('bb22560000')),
  'rate_setter_writes_record_plus10':b[0x1f4e9:0x1f4ef]==bytes.fromhex('8b45f4894210'),
  'rate_setter_calls_miles_wrapper':rel32(b,0x1f507)==0x38d8c,
 }
 bad=[k for k,v in checks.items() if not v]
 if bad: raise SystemExit('v49 invariant failed: '+repr(bad))
 out={'schema':'openazrael.playback_rate_callsites','version':49,'status':'PASS','exe_sha256':sha,'invariants':checks,
 'result':{'setter':'0x1F4A5','direct_callsites':[hex(x) for x in cs],'explicit_values':[22050,22050,22050],
 'conclusion':'Every direct call to the engine playback-rate setter found in the demo executable supplies 22050. No direct demo call site changes this setter to another value.',
 'confidence':'HIGH','scope':'direct calls in demo R.EXE only'},
 'interpretation':{'classic_demo_playback_rate':22050,'confidence':'HIGH','caveat':'This does not prove indirect/function-pointer calls are impossible, nor does it generalize beyond the demo executable.'},
 'amb_literal_1000':{'status':'HOLD','note':'The 1000 argument is preserved as an unresolved packed-ABI parameter. v49 deliberately does not label it without a clean downstream semantic binding.'},
 'next':['Resolve the packed ABI carrying the AMB literal 1000 through 0xD523 -> 0x1EF44 -> 0x1EDD7.','Resume exact 3D attenuation and pan reconstruction.']}
 Path(a.out).write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
 print(json.dumps({'status':'PASS','checks':len(checks),'direct_callsites':[hex(x) for x in cs],'values':[22050]*3},indent=2))
if __name__=='__main__': main()
