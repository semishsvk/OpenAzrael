#!/usr/bin/env python3
import argparse,json,math,hashlib
from pathlib import Path
EXPECTED='381e4f5c61e4bb8c27f06b1944e6673bbebc39ca219cc08fb9f948da2ca37c00'

def trunc0(x): return math.trunc(x)

def pan_from_headings(listener_deg, source_deg):
    # Literal translation of 0xCE29..0xCF11 after heading extraction.
    a=float(listener_deg); b=float(source_deg); mode=1
    if a <= 180.0 and b > 180.0:
        d=360.0-b+a
        if d > 180.0: d=-(360.0-d)
    else:
        d=-(360.0-a+b)
        if d < -180.0: d += 360.0
    if d > 90.0:
        mode=2; d=180.0-d
    elif d < -90.0:
        mode=2; d=-180.0-d
    pan=trunc0(d*63.0/90.0+64.0)
    return {'pan':pan,'folded_angle_deg':d,'mode_divisor':mode}

def attenuation(distance, global_volume=99, mode_divisor=1):
    # 0xCF3C..0xCF8E. FPU conversion helper 0x2442A truncates toward zero.
    raw=99 if distance==0 else trunc0(15000.0/distance)
    divided=trunc0(raw/mode_divisor)
    clamped=min(divided,99)
    final=trunc0(global_volume*clamped/99)
    return {'raw':raw,'after_mode_divisor':divided,'clamped':clamped,'volume':final}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('exe'); ap.add_argument('--out',required=True); a=ap.parse_args()
    sha=hashlib.sha256(Path(a.exe).read_bytes()).hexdigest()
    if sha!=EXPECTED: raise SystemExit('unexpected R.EXE hash')
    pan_cases=[(0,0),(0,45),(0,90),(0,135),(0,180),(0,225),(0,270),(0,315),(0,360),(90,0),(180,0),(270,0)]
    pv=[{'listener_heading':x,'source_heading':y,**pan_from_headings(x,y)} for x,y in pan_cases]
    av=[]
    for d in [0,50,100,150,151,300,1000,5000,15000,30000]:
        for m in [1,2]: av.append({'distance':d,'global_volume':99,'mode_divisor':m,**attenuation(d,99,m)})
    checks={
      'pan_center_same_heading':pan_from_headings(0,0)['pan']==64,
      'pan_plus_90':pan_from_headings(0,270)['pan']==127,
      'pan_minus_90':pan_from_headings(0,90)['pan']==1,
      'pan_rear_folds_and_halves_gain':pan_from_headings(0,180)=={'pan':64,'folded_angle_deg':0.0,'mode_divisor':2},
      'distance_zero_99':attenuation(0)['volume']==99,
      'distance_150_clamps_99':attenuation(150)['volume']==99,
      'distance_151_below_clamp':attenuation(151)['volume']==99, # trunc(15000/151)=99
      'distance_152_is_98':attenuation(152)['volume']==98,
      'distance_1000_is_15':attenuation(1000)['volume']==15,
      'rear_mode_halves_distance_gain':attenuation(1000,99,2)['volume']==7,
      'global_volume_scaling':attenuation(1000,50,1)['volume']==7,
    }
    if not all(checks.values()): raise SystemExit(checks)
    out={'schema':'openazrael.classic_3d_reference','version':59,'status':'PASS','exe_sha256':sha,'invariants':checks,
      'constants':{'degrees_per_half_turn':180.0,'pi':3.141592,'full_turn':360.0,'right_angle':90.0,'pan_span':63.0,'pan_center':64.0,'distance_numerator':15000.0,'volume_ceiling':99},
      'pan_reference':{'confidence':'HIGH_AFTER_HEADING_EXTRACTION','scope':'Exact translation of 0xCE29..0xCF11. Heading extraction helper identity remains HOLD, so these golden vectors intentionally use headings as inputs, not XYZ vectors.','golden_vectors':pv},
      'attenuation_reference':{'confidence':'HIGH_WITH_RUNTIME_GLOBAL_VOLUME_PARAMETER','scope':'Exact integer/FPU structure of 0xCF3C..0xCF8E using K_DISTANCE=15000 from v58. GLOBAL_VOLUME at 0x615E remains runtime state and is parameterized.','golden_vectors':av},
      'corrections':['Do not claim full XYZ-to-pan parity yet: helper 0x30D9E/0x30D7A heading semantics are not independently closed.','Do not hard-code GLOBAL_VOLUME=99; 99 is the 3D gain ceiling/normalizer, while runtime global volume is a separate signed word.'],
      'decision':'ACCEPT angle-domain pan and distance-domain attenuation reference functions + golden vectors. HOLD complete XYZ spatializer until heading helper and global-volume initialization/state are closed.',
      'next':['Identify helper 0x30D7A/0x30D9E mathematically and bind normalized X/Z to heading.','Trace 0x615E initialization/UI scaling to characterize runtime global-volume range/default.','Then port the reference functions into Godot Classic renderer and run parity fixtures.']}
    Path(a.out).write_text(json.dumps(out,indent=2),encoding='utf8')
    print(json.dumps({'status':'PASS','checks':len(checks),'pan_vectors':len(pv),'attenuation_vectors':len(av)},indent=2))
if __name__=='__main__': main()
