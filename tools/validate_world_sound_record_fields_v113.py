#!/usr/bin/env python3
from pathlib import Path
import json, sys

ROOT=Path(__file__).resolve().parents[1]
RESULT=ROOT/'data/world_sound_record_fields_v113.json'

def fail(msgs):
    print('OpenAzrael v113 WORLD sound-record validation: FAIL')
    for m in msgs: print(' -',m)
    return 1

def main():
    errors=[]
    try:
        d=json.loads(RESULT.read_text(encoding='utf-8'))
    except Exception as exc:
        return fail([f'result load: {exc}'])
    if d.get('schema')!='openazrael.world_sound_record_fields': errors.append('schema drift')
    if d.get('version')!=113 or d.get('status')!='PASS': errors.append('version/status drift')
    oc=d.get('ordered_correspondence',{})
    if (oc.get('puzzles_records'),oc.get('world_records'),oc.get('lcs_matches'))!=(40,44,38): errors.append('ordered correspondence drift')
    if oc.get('puzzles_only_tokens')!=['995','995']: errors.append('PUZZLES-only token drift')
    if oc.get('world_only_tokens')!=['sr27keys','996','s152v2','s152v2','s121','s188']: errors.append('WORLD-only token drift')
    layout=d.get('record_layout',{})
    if layout.get('size')!=27: errors.append('record size drift')
    if layout.get('opcode',{}).get('offset')!=0 or layout.get('opcode',{}).get('value')!=40: errors.append('opcode layout drift')
    if layout.get('sound_stem',{}).get('offset')!=1: errors.append('sound stem layout drift')
    if layout.get('section0_object_index',{}).get('offset')!=13: errors.append('section0 index offset drift')
    if layout.get('room_id',{}).get('offset')!=15: errors.append('room-id offset drift')
    if layout.get('room_id',{}).get('mapping')!={'0':'R1','1':'R7','2':'R8'}: errors.append('room mapping drift')
    if layout.get('room_id',{}).get('direct_xaf_manifest_matches')!=35 or layout.get('room_id',{}).get('remaining_alias_matches')!=3: errors.append('room evidence count drift')
    if layout.get('tail_17_26',{}).get('meaning')!='UNKNOWN/HOLD': errors.append('tail HOLD boundary drift')
    chain=d.get('spatial_playback_chain',{})
    expected={
        'handler_object1_offset_hex':'0x191e9',
        'section0_array_global_hex':'0x43890',
        'current_context_global_hex':'0x43888',
        'section0_name_runtime_offset_hex':'0x34',
        'filename_format':'%s.WAV',
        'dynamic_3d_start_object1_offset_hex':'0xd155',
    }
    for k,v in expected.items():
        if chain.get(k)!=v: errors.append(f'playback-chain drift: {k}')
    aligned=d.get('ordered_alignment',[])
    if len(aligned)!=38: errors.append('aligned record count drift')
    if any(x.get('room_id') not in (0,1,2) for x in aligned): errors.append('invalid aligned room id')
    if any(not (0 <= int(x.get('section0_index',-1)) < 1303) for x in aligned): errors.append('invalid section0 index')
    if len(d.get('referenced_section0_objects',[]))!=15: errors.append('referenced section0 object count drift')
    # Result must stay metadata-only/source-safe.
    forbidden_keys={'raw','raw_hex','block_hex','payload_hex','bytes_hex'}
    def walk(x,path='root'):
        if isinstance(x,dict):
            for k,v in x.items():
                if k.lower() in forbidden_keys: errors.append(f'forbidden raw payload key at {path}.{k}')
                walk(v,f'{path}.{k}')
        elif isinstance(x,list):
            for i,v in enumerate(x): walk(v,f'{path}[{i}]')
    walk(d)
    if errors: return fail(errors)
    print('OpenAzrael v113 WORLD sound-record validation: PASS')
    print(' ordered mapping: 38/40 PUZZLES actions')
    print(' direct room matches: 35 + 3 aliases')
    print(' referenced section-0 objects: 15')
    print(' source-safe metadata boundary: PASS')
    return 0

if __name__=='__main__': raise SystemExit(main())
