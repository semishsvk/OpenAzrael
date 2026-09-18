#!/usr/bin/env python3
from pathlib import Path
import json, sys

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'data/world_action_lifecycle_v115.json'
errors=[]
try:
    d=json.loads(P.read_text(encoding='utf-8'))
except Exception as e:
    print('OpenAzrael v115 WORLD action lifecycle validation: FAIL')
    print(' - load:',e)
    raise SystemExit(1)

if d.get('schema')!='openazrael.world_action_record_lifecycle_audit' or d.get('version')!=115 or d.get('status')!='PASS':
    errors.append('schema/version/status drift')

pop=d.get('population_path',{})
if pop.get('record27_insert_function_hex')!='0x295b0' or pop.get('direct_call_sites')!=['0x296ec']:
    errors.append('27-byte insert path drift')
if pop.get('record37_insert_function_hex')!='0x295f4' or pop.get('direct_call_sites_37')!=['0x2968a']:
    errors.append('37-byte insert path drift')
alloc=pop.get('immediate_27_alloc_matches',[])
if alloc!=[{'call_site_hex':'0x29712','mov_site_hex':'0x29703'}]:
    errors.append('27-byte immediate allocation audit drift')

sched=d.get('shallow_runtime_schedule',{})
if sched.get('condition_scan_hex')!='0x2990c' or sched.get('condition_scan_direct_call_hex')!='0x29ddf':
    errors.append('condition/schedule path drift')
if sched.get('pending_group_count_global_hex')!='0x438b0' or sched.get('pending_group_array_global_hex')!='0x438b4':
    errors.append('pending-group globals drift')
if sched.get('entry_size')!=6:
    errors.append('pending-group entry size drift')
layout=sched.get('entry_layout',{})
if layout.get('count27')!={'offset':0,'size':2,'source':'nested object +6'}:
    errors.append('pending count27 layout drift')
if layout.get('pointer_array27')!={'offset':2,'size':4,'source':'nested object +8'}:
    errors.append('pending pointer-array layout drift')

path=d.get('dispatch_path',{})
if path.get('dispatcher_hex')!='0x18698' or path.get('pending_group_stride')!=6:
    errors.append('dispatcher/stride drift')
if path.get('sound_handler_hex')!='0x191e9' or path.get('sound_handler_mutates_record') is not False:
    errors.append('sound-handler mutation boundary drift')

life=d.get('lifecycle_conclusion',{})
if 'No copy/normalization step' not in life.get('finding',''):
    errors.append('lifecycle copy boundary drift')
if 'upstream/HOLD' not in life.get('tail_implication',''):
    errors.append('tail origin HOLD boundary drift')
if 'remains HOLD' not in life.get('producer_boundary',''):
    errors.append('producer HOLD boundary drift')

checks=d.get('checks',{})
if len(checks)!=20 or not all(checks.values()):
    errors.append('machine invariant drift')

forbidden={'raw','raw_hex','block_hex','payload_hex','bytes_hex','tail_hex','record_hex','record_bytes'}
def walk(x,path='root'):
    if isinstance(x,dict):
        for k,v in x.items():
            if k.lower() in forbidden:
                errors.append(f'forbidden raw payload field at {path}.{k}')
            walk(v,f'{path}.{k}')
    elif isinstance(x,list):
        for i,v in enumerate(x): walk(v,f'{path}[{i}]')
walk(d)

if errors:
    print('OpenAzrael v115 WORLD action lifecycle validation: FAIL')
    for e in errors: print(' -',e)
    sys.exit(1)
print('OpenAzrael v115 WORLD action lifecycle validation: PASS')
print(' population: reader-only in audited direct insert/immediate allocation classes')
print(' schedule: 6-byte shallow count+pointer-array reference')
print(' dispatch: original 27-byte record pointer, in place')
print(' tail origin: upstream UNKNOWN/HOLD')
