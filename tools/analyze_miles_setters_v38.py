#!/usr/bin/env python3
import argparse, hashlib, json, struct
from pathlib import Path
EXPECTED='381e4f5c61e4bb8c27f06b1944e6673bbebc39ca219cc08fb9f948da2ca37c00'
def u32(d,o): return struct.unpack_from('<I',d,o)[0]
def build_obj1(raw):
    lo=raw.find(b'LE')
    # Bound demo has earlier incidental bytes; use validated header location.
    lo=0x37d4c
    if raw[lo:lo+2]!=b'LE': raise SystemExit('validated LE header missing')
    le=raw[lo:]; ot=u32(le,0x40); dp=u32(le,0x80)
    size=struct.unpack_from('<I',le,ot)[0]
    return bytes(le[dp:dp+size])
def relcall(b,o):
    if b[o]!=0xE8: raise AssertionError(f'no CALL at {o:x}')
    return o+5+struct.unpack_from('<i',b,o+1)[0]
def imm32_push(b,o):
    if b[o]!=0x68: raise AssertionError(f'no PUSH imm32 at {o:x}')
    return u32(b,o+1)
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('exe'); ap.add_argument('--out',required=True); a=ap.parse_args()
    raw=Path(a.exe).read_bytes(); sha=hashlib.sha256(raw).hexdigest(); b=build_obj1(raw)
    # v37 wrappers -> backend wrappers
    vol_wrapper=0x1f5fc; pan_wrapper=0x1f6f1
    vol_backend=relcall(b,0x1f683); pan_backend=relcall(b,0x1f7a0)
    assert vol_backend==0x38e02 and pan_backend==0x38e78
    # Backend diagnostic paths push adjacent format-string offsets.
    vol_diag=imm32_push(b,0x38e51); pan_diag=imm32_push(b,0x38ec7)
    assert vol_diag==0x41be and pan_diag==0x41de and pan_diag-vol_diag==0x20
    # Independently find the exact diagnostic strings in original executable; their byte spacing is preserved.
    sv=b'AIL_set_sample_volume(0x%X,%d)'; sp=b'AIL_set_sample_pan(0x%X,%d)'
    fv=raw.find(sv); fp=raw.find(sp)
    assert fv>=0 and fp>=0 and fp-fv==0x20
    # Real backend dispatch calls are likewise adjacent by 0x30.
    vol_dispatch=relcall(b,0x38e6e); pan_dispatch=relcall(b,0x38ee4)
    assert vol_dispatch==0x4c3b8 and pan_dispatch==0x4c3e8 and pan_dispatch-vol_dispatch==0x30
    out={
      'schema':'openazrael.miles_setter_identity','version':38,'exe_sha256':sha,
      'evidence':{
        'volume':{'engine_wrapper':'0x1F5FC','backend_wrapper':'0x38E02','diagnostic_push':'0x41BE','diagnostic_string':'AIL_set_sample_volume(0x%X,%d)','dispatch':'0x4C3B8'},
        'pan':{'engine_wrapper':'0x1F6F1','backend_wrapper':'0x38E78','diagnostic_push':'0x41DE','diagnostic_string':'AIL_set_sample_pan(0x%X,%d)','dispatch':'0x4C3E8'},
        'independent_spacing_invariant':{'diagnostic_push_delta':32,'raw_exe_string_delta':fp-fv,'dispatch_delta':pan_dispatch-vol_dispatch}
      },
      'conclusion':{
        '0x1F5FC_role':'SET_SAMPLE_VOLUME','0x1F6F1_role':'SET_SAMPLE_PAN',
        'confidence':'HIGH',
        'reason':'Each engine wrapper reaches a distinct backend wrapper whose diagnostic-format slot has exactly the same 0x20 ordering/spacing as the literal Miles volume and pan diagnostics in R.EXE; their final dispatch routines are also distinct and adjacent.'
      },
      'impact':{'v37_distance_path':'CONFIRMED_VOLUME_PATH','v37_directional_path':'CONFIRMED_PAN_PATH','exact_attenuation_formula':'HOLD','exact_pan_formula':'HOLD'},
      'invariants':{'exe_hash_matches':sha==EXPECTED,'wrapper_calls_match':True,'diagnostic_spacing_matches':True,'dispatch_pair_matches':True}
    }
    if not all(out['invariants'].values()): raise SystemExit('v38 invariant failed')
    Path(a.out).write_text(json.dumps(out,indent=2),encoding='utf8')
    print(json.dumps({'status':'PASS','volume_backend':hex(vol_backend),'pan_backend':hex(pan_backend),'raw_string_delta':fp-fv,'dispatch_delta':pan_dispatch-vol_dispatch},indent=2))
if __name__=='__main__': main()
