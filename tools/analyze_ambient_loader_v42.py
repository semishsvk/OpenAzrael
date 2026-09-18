#!/usr/bin/env python3
import argparse, hashlib, json, re, struct
from pathlib import Path
EXPECTED='381e4f5c61e4bb8c27f06b1944e6673bbebc39ca219cc08fb9f948da2ca37c00'
def u32(d,o): return struct.unpack_from('<I',d,o)[0]
def build_obj1(raw):
    lo=0x37d4c
    if raw[lo:lo+2]!=b'LE': raise SystemExit('validated LE header missing')
    le=raw[lo:]; ot=u32(le,0x40); pm=u32(le,0x48); dp=u32(le,0x80); ps=u32(le,0x28)
    size,base,flags,first,npg,res=struct.unpack_from('<IIIIII',le,ot); b=bytearray(size)
    for lp in range(npg):
        e=le[pm+4*(first-1+lp):pm+4*(first-1+lp)+4]; pn=(e[0]<<16)|(e[1]<<8)|e[2]
        if not pn: continue
        src=lo+dp+(pn-1)*ps; dst=lp*ps; n=min(ps,size-dst,max(0,len(raw)-src)); b[dst:dst+n]=raw[src:src+n]
    return bytes(b)
def parse_snd(path):
    out=[]
    for line in path.read_text(encoding='latin1').splitlines():
        m=re.match(r'^SAMPLE\s+(-?\d+),(-?\d+),(-?\d+)\s+(\S+)$',line.strip(),re.I)
        if m: out.append({'xyz':[int(m.group(1)),int(m.group(2)),int(m.group(3))],'sample':m.group(4).lower()})
    return out
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('exe'); ap.add_argument('--snd-dir',required=True); ap.add_argument('--out',required=True); a=ap.parse_args()
    raw=Path(a.exe).read_bytes(); sha=hashlib.sha256(raw).hexdigest(); b=build_obj1(raw)
    # Exact byte-level invariants around the AMB loader and slot-specific 3D sample starter.
    checks={
      'exe_hash':sha==EXPECTED,
      'loader_entry_shape':b[0xd7bf:0xd7c7]==bytes.fromhex('53515657c8e00000'),
      'loader_clears_first_three_slots':b[0xd7d9:0xd7f7]==bytes.fromhex('31c9eb120fbfd189f0e856ffffff6bc328c6040600410fb7d983fb037ce6'),
      'loader_builds_room_filename':b[0xd7f7:0xd81a]==bytes.fromhex('0fbf457a50682a1a00008d45a250e8ec8b010083c40cba341a00008d45a2e8ea870100'),
      'loader_parse_call_has_five_outputs':b[0xd832:0xd856]==bytes.fromhex('8d45a2508d4572508d456e508d456a508d45065068361a0000ff7576e84ad2010083c41c'),
      'loader_caps_ambient_records_at_three':b[0xd870:0xd878]==bytes.fromhex('0fb7c183f8037c2c'),
      'loader_passes_parsed_xyz_to_slot_starter':b[0xd8a4:0xd8d0]==bytes.fromhex('6a0068e80300006a006a010fb7c15068b4f60000ff7572ff756eff756a0fb7f98d5da289fa89f0e853fcffff'),
      'slot_starter_copies_xyz_to_emitter_table':b[0xd57b:0xd589]==bytes.fromhex('89c78dbfe82702008d7514a5a5a5'),
      'slot_starter_uses_stride_24':b[0xd550:0xd578]==bytes.fromhex('0fb7c26bc0180fbf80f427020083f8ff0f840b0000000fbfd28b45f0e8cc0100000fb745fc6bc018'),
      'slot_starter_spatializes_immediately':b[0xd5b0:0xd5dc]==bytes.fromhex('ff35e4270200ff35e0270200ff35dc270200ff35d8270200ff35d4270200ff35d02702008b45f0e805f8ffff'),
      'move_api_overwrites_xyz':b[0xd6ce:0xd6f5]==bytes.fromhex('56575589e50fbff26bf6180fbf86f427020083f8ff740c8dbee82702008d7510a5a5a55d5f5ec2'),
      'translate_api_adds_xyz_delta':b[0xd6f7:0xd73d].startswith(bytes.fromhex('5589e50fbfc26bc0180fbf90f427020083faff742d')),
      'stop_all_iterates_seven_slots':b[0xd787:0xd7be].startswith(bytes.fromhex('53515231c9eb01410fb7d983fb077d24')),
      'diagnostic_strings_present':all(x in raw for x in [b'AMB%d.SND',b'SAMPLE',b'Too many ambient sounds',b'StartAmbientSoundFX',b'END3DSAMPLE'])
    }
    snd_dir=Path(a.snd_dir); snd={p.name:parse_snd(p) for p in sorted(snd_dir.glob('AMB*.SND'))}
    snd_counts={k:len(v) for k,v in snd.items()}
    checks['demo_has_three_amb_files']=set(snd)=={'AMB0.SND','AMB1.SND','AMB2.SND'}
    checks['demo_amb_counts_fit_three_slot_loader']=snd_counts=={'AMB0.SND':2,'AMB1.SND':3,'AMB2.SND':2}
    checks['demo_total_emitters_seven']=sum(snd_counts.values())==7
    if not all(checks.values()):
        raise SystemExit('v42 invariant failed: '+repr({k:v for k,v in checks.items() if not v}))
    out={
      'schema':'openazrael.ambient_loader_pipeline','version':42,'status':'PASS','exe_sha256':sha,'invariants':checks,
      'loader':{
        'routine':'object1:0xD7BF','confidence':'HIGH',
        'room_id_input':'DX / saved at [EBP+0x7A]','ambient_slot_range':[0,2],
        'behavior':['stops/clears slots 0..2 before loading a room ambient file','constructs a room-specific filename','opens and iteratively parses records','accepts at most three ambient records','passes parsed XYZ plus sample name/state to slot-specific starter 0xD523']
      },
      'runtime_emitter_record':{
        'table_base':'0x227E8','stride_bytes':24,'total_slots':7,'ambient_reserved_slots':[0,1,2],'dynamic_slots':[3,4,5,6],
        'xyz_offsets':[0,4,8],'sample_handle_offset':'0x0C','confidence':'HIGH'
      },
      'routines':{
        '0xD523':{'role':'slot-specific 3D sample start','copies_xyz':'stack [EBP+14..1C] -> emitter[slot].xyz','immediate_spatialization':'calls 0xCDE1 with cached listener position+orientation','confidence':'HIGH'},
        '0xD155':{'role':'dynamic 3D sample start','allocation':'searches free slot beginning at 3 and below 7','confidence':'HIGH'},
        '0xD6CE':{'role':'set emitter XYZ for existing slot','confidence':'HIGH'},
        '0xD6F7':{'role':'add XYZ delta to existing emitter','confidence':'HIGH'},
        '0xD73D':{'role':'stop/release one 3D sample slot','confidence':'HIGH'},
        '0xD787':{'role':'stop/release all seven 3D sample slots','confidence':'HIGH'}
      },
      'demo_snd':snd,
      'end_to_end_model':[
        'ROOM id -> room-specific AMB file (filename-format identity is supported by co-located R.EXE strings; exact relocated format pointer remains unbound).',
        'AMB parser reads a token/string + three numeric coordinates + sample filename/state fields.',
        'For each of at most three room ambient records, 0xD523 copies XYZ into emitter slot 0..2 and starts the sample.',
        '0xD523 immediately calls 0xCDE1, which uses emitter.xyz + cached listener position/orientation to derive Miles pan and volume.',
        'The demo AMB files contain 2 + 3 + 2 = seven placements across rooms, while runtime room ambience reserves three simultaneous slots.'
      ],
      'confidence':{
        'ambient_loader_routine':'HIGH','ambient_slots_0_2':'HIGH','dynamic_slots_3_6':'HIGH','emitter_record_xyz_layout':'HIGH','AMB_filename_string_binding':'HIGH_BUT_NOT_EXACT_XREF','exact_scan_format_pointer':'HOLD','exact_numeric_attenuation':'HOLD','exact_pan_formula':'HOLD'
      },
      'next':['Resolve the relocated format/string references used by 0xD7BF to bind AMB%d.SND/SAMPLE/END exactly rather than by behavioral+string evidence.','Trace 0xD523 sample-name path through 0x1EF44 to bind parsed filename to the Miles sample handle.','Then mirror the verified 3-slot ambient reservation and 4-slot dynamic reservation in ClassicAudioRenderer.']
    }
    Path(a.out).write_text(json.dumps(out,indent=2,sort_keys=True)+'\n',encoding='utf8')
    print(json.dumps({'status':'PASS','ambient_loader':'HIGH','ambient_slots':'0..2','dynamic_slots':'3..6','demo_emitters':sum(snd_counts.values()),'all_invariants':True},indent=2))
if __name__=='__main__': main()
