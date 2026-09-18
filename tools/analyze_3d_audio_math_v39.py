#!/usr/bin/env python3
import argparse, hashlib, json, struct
from pathlib import Path
EXPECTED='381e4f5c61e4bb8c27f06b1944e6673bbebc39ca219cc08fb9f948da2ca37c00'
def u32(d,o): return struct.unpack_from('<I',d,o)[0]
def build_obj1(raw):
    lo=0x37d4c
    if raw[lo:lo+2]!=b'LE': raise SystemExit('validated LE header missing')
    le=raw[lo:]; ot=u32(le,0x40); dp=u32(le,0x80); size=u32(le,ot)
    return bytes(le[dp:dp+size])
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('exe'); ap.add_argument('--out',required=True); a=ap.parse_args()
    raw=Path(a.exe).read_bytes(); sha=hashlib.sha256(raw).hexdigest(); b=build_obj1(raw)
    # Exact raw-code invariants for the v37/v38 HIGH-confidence 3D audio update core.
    checks={
      'distance_constant_load': b[0xcf4b:0xcf51]==bytes.fromhex('dd0594190000'),
      'distance_division': b[0xcf51:0xcf54]==bytes.fromhex('dc75e4'),
      'distance_to_integer': b[0xcf54]==0xe8 and b[0xcf59:0xcf5c]==bytes.fromhex('db5df4'),
      'zero_distance_fallback_99': b[0xcf5e:0xcf65]==bytes.fromhex('c745f463000000'),
      'mode_division': b[0xcf65:0xcf6f]==bytes.fromhex('8b45f499f77df08945f4'),
      'upper_clamp_99': b[0xcf6f:0xcf7b]==bytes.fromhex('83f8637e07c745f463000000'),
      'global_scale_load': b[0xcf7b:0xcf82]==bytes.fromhex('0fbf055e610000'),
      'scale_multiply': b[0xcf82:0xcf86]==bytes.fromhex('0faf45f4'),
      'normalize_by_99': b[0xcf86:0xcf8e]==bytes.fromhex('bb6300000099f7fb'),
      'volume_wrapper_call': b[0xcfb8]==0xe8,
      'pan_math_uses_angle_constants': all(b[o:o+2] in (b'\xdc\x1d',b'\xdd\x05',b'\xdc\x0d',b'\xdc\x35',b'\xdc\x05') for o in [0xce2c,0xce65,0xce74,0xcea2,0xcebc,0xcece,0xced9,0xcefa,0xcf00,0xcf06]),
    }
    if not all(checks.values()): raise SystemExit('v39 invariant failed')
    placeholders={}
    for o in [0x1954,0x195c,0x1964,0x196c,0x1974,0x197c,0x1984,0x198c,0x1994,0x615e]:
        n=2 if o==0x615e else 8
        placeholders[hex(o)]={'raw_bytes':b[o:o+n].hex(),'warning':'UNRELOCATED_ADDRESS_PLACEHOLDER_NOT_RUNTIME_DATA'}
    out={
      'schema':'openazrael.audio_3d_math','version':39,'exe_sha256':sha,
      'status':'PASS','invariants':checks,
      'volume_path':{
        'confidence':'HIGH',
        'symbolic_formula':'v0 = (distance == 0) ? 99 : FPU_INT(K_DISTANCE / distance); v1 = trunc_int(v0 / mode_divisor); v2 = min(v1, 99); volume = trunc_int((GLOBAL_VOLUME_SCALE * v2) / 99)',
        'distance_source':'Euclidean/vector magnitude helper 0x2FCDC from v37',
        'setter':'AIL_set_sample_volume path confirmed HIGH in v38',
        'K_DISTANCE':'HOLD_RUNTIME_RELOCATED_DATA',
        'GLOBAL_VOLUME_SCALE':'HOLD_RUNTIME_RELOCATED_SIGNED_WORD',
        'mode_divisor':'runtime local -0x10; initialized to 1 and conditionally changed to 2 by directional/angle logic',
        'hard_ceiling':99,
        'zero_distance_value':99
      },
      'pan_path':{
        'confidence':'HIGH_STRUCTURE_EXACT_CONSTANTS_HOLD',
        'description':'The same core derives an angular/directional integer using several relocated floating constants, then sends that integer through the v38-confirmed AIL_set_sample_pan path.',
        'setter':'AIL_set_sample_pan path confirmed HIGH in v38',
        'exact_constants':'HOLD_RUNTIME_RELOCATED_DATA'
      },
      'critical_correction':{
        'finding':'Addresses 0x1954..0x1994 and 0x615E visible in the unrelocated object-1 bytes are relocation placeholders, not locations from which numeric constants may be read directly.',
        'evidence':'Those offsets fall inside coherent executable code in the raw object image; interpreting their bytes as doubles/words produces instruction bytes, not runtime audio constants.',
        'impact':'Earlier plan to decode those raw offsets as floating constants is withdrawn. Exact Classic attenuation/pan constants must wait for a trusted relocation/runtime-data reconstruction or dynamic observation.',
        'confidence':'VERIFIED_FOR_RAW_IMAGE_INTERPRETATION'
      },
      'raw_placeholder_audit':placeholders,
      'implementation_decision':'Do not bake guessed constants into Classic Audio. The symbolic volume algorithm is safe to encode as forensic metadata, but runtime Classic renderer remains on HOLD for exact numeric emulation.',
      'next':['Recover runtime targets/initializers for K_DISTANCE and GLOBAL_VOLUME_SCALE without treating raw placeholders as data.','Trace callers of 0xCDE1 to determine arguments and the mode-divisor condition.','Only after constants are independently validated, add an exact Classic attenuation implementation plus golden-vector tests.']
    }
    if sha!=EXPECTED: raise SystemExit('unexpected R.EXE hash')
    Path(a.out).write_text(json.dumps(out,indent=2),encoding='utf8')
    print(json.dumps({'status':'PASS','volume_formula':out['volume_path']['symbolic_formula'],'all_invariants':all(checks.values()),'correction':out['critical_correction']['confidence']},indent=2))
if __name__=='__main__': main()
