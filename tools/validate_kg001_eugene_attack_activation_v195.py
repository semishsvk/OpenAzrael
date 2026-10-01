#!/usr/bin/env python3
from pathlib import Path
import argparse, hashlib, json, struct, sys

EXPECTED_EXE='381e4f5c61e4bb8c27f06b1944e6673bbebc39ca219cc08fb9f948da2ca37c00'
EXPECTED_ANI='4125d9693137f74020209fc2f7f834cb64ce232cbabd4e7a8fe0199d9933b636'
LE_OFFSET=0x37D4C
EARLY_STRING_BASE=0x11C558
LATE_STRING_BIAS=0x2AA8

def u32(b,o): return struct.unpack_from('<I',b,o)[0]
def build_objects(raw):
    le=raw[LE_OFFSET:]
    if le[:2]!=b'LE': raise SystemExit('validated LE header missing')
    page_size=u32(le,0x28); obj_table=u32(le,0x40); obj_count=u32(le,0x44); page_map=u32(le,0x48); data_pages=u32(le,0x80)
    out=[]
    for idx in range(obj_count):
        size,base,flags,first,count,_=struct.unpack_from('<IIIIII',le,obj_table+24*idx)
        span=bytearray(count*page_size)
        for lp in range(count):
            e=le[page_map+4*(first-1+lp):page_map+4*(first-1+lp)+4]
            phys=(e[0]<<16)|(e[1]<<8)|e[2]
            if not phys: continue
            src=LE_OFFSET+data_pages+(phys-1)*page_size; dst=lp*page_size
            n=min(page_size,max(0,len(raw)-src)); span[dst:dst+n]=raw[src:src+n]
        out.append({'virtual':bytes(span[:size]),'page_span':bytes(span),'virtual_size':size,'base':base})
    return out

def cstr(b,o,limit=128):
    if not (0<=o<len(b)): return None
    e=b.find(b'\0',o,min(len(b),o+limit))
    return None if e<0 else b[o:e].decode('latin1')
def call_target(b,site):
    if b[site]!=0xE8: return None
    return site+5+int.from_bytes(b[site+1:site+5],'little',signed=True)
def calls_to(b,target):
    return [i for i in range(len(b)-5) if b[i]==0xE8 and call_target(b,i)==target]

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--exe',required=True); ap.add_argument('--ani',required=True); ap.add_argument('--out'); a=ap.parse_args()
    exe=Path(a.exe).read_bytes(); ani=Path(a.ani).read_bytes(); objs=build_objects(exe); o1=objs[0]['virtual']; o1p=objs[0]['page_span']; o2p=objs[1]['page_span']
    ani_text=ani.replace(b'\r',b'').replace(b'\x1a',b'').decode('latin1')
    names=['REST','WALK','SLEEP','START_RUN','RUN','END_RUN','PICKUP','DROP','ROAR','SNIFF','AWAKE','SHOT','ATTACK','DEATH_TWITCH','DEAD','NOLOOP1','NOLOOP2','NOLOOP3','FLOAT','FACE_YOU','SHOT_RECOVER']
    enum_actual=[cstr(o2p,0x6BE4+i*0x0D-LATE_STRING_BIAS) for i in range(len(names))]
    checks={
      'exe_hash':hashlib.sha256(exe).hexdigest()==EXPECTED_EXE,
      'ani_hash':hashlib.sha256(ani).hexdigest()==EXPECTED_ANI,
      'ani_health_2':'HEALTH 2' in ani_text,
      'ani_ranged_30':'RANGED 30' in ani_text,
      'ani_attack_53_70':'ATTACK 53-70' in ani_text,
      'ani_trigger_60':'TRIGGER 60 EUGROAR.WAV 200' in ani_text,
      'health_parser_token':cstr(o1p,EARLY_STRING_BASE+0x1D8D)=='HEALTH',
      'health_parser_store':o1[0xF39D:0xF3A6]==bytes.fromhex('e8 d5 99 01 00 66 89 42 0c'),
      'ranged_parser_token':cstr(o1p,EARLY_STRING_BASE+0x1DAB)=='RANGED',
      'ranged_parser_store':o1[0xF4F0:0xF4F9]==bytes.fromhex('e8 82 98 01 00 66 89 42 18'),
      'enum_table_exact':enum_actual==names,
      'enum_is_one_based':o1[0xFA45:0xFA50]==bytes.fromhex('b6 01 8a 18 88 b4 24 80 01 00 00'),
      'enum_stride_13':o1[0xFA82:0xFA8B]==bytes.fromhex('6b f6 0d 81 c6 e4 6b 00 00'),
      'attack_string_anchor':cstr(o1p,EARLY_STRING_BASE+0x25DB)=='AttackPlayer',
      'attack_action_anchor_push':o1[0x13ED0:0x13EDA]==bytes.fromhex('68 b6 25 00 00 68 db 25 00 00'),
      'attack_action_initial_run_code_5':o1[0x13EE2:0x13EE7]==bytes.fromhex('bb 05 00 00 00'),
      'attack_action_initial_animation_call':call_target(o1,0x13EEB)==0x12014,
      'attack_action_sets_field_08_minus1':o1[0x13EF4:0x13EFA]==bytes.fromhex('66 c7 47 08 ff ff'),
      'attack_action_calls_helper':call_target(o1,0x13EFA)==0x144DC,
      'attack_helper_reads_ranged':o1[0x14544:0x1454B]==bytes.fromhex('66 8b 46 18 0f af c0'),
      'attack_helper_code_0d':o1[0x1458B:0x14590]==bytes.fromhex('bb 0d 00 00 00'),
      'attack_helper_saves_previous_selector':o1[0x14590:0x1459E]==bytes.fromhex('8a 86 60 02 00 00 89 ca 88 86 61 02 00 00'),
      'attack_helper_sets_active_flag':o1[0x145A0:0x145A6]==bytes.fromhex('66 c7 46 22 01 00'),
      'attack_helper_requests_attack':call_target(o1,0x145A6)==0x12014,
      'attack_helper_restores_saved_selector':o1[0x145BD:0x145D0]==bytes.fromhex('89 ca 8b 9e 5e 02 00 00 89 f8 c1 fb 18 66 c7 46 22 00 00'),
      'attack_helper_restore_call':call_target(o1,0x145D0)==0x12014,
      'attack_helper_movement_call':call_target(o1,0x145D9)==0x12714,
      'old_12584_not_attack_helper':calls_to(o1,0x12584)==[0x2F88,0x300F],
    }
    failed=[k for k,v in checks.items() if not v]
    out={'schema':'openazrael.kg001.eugene_attack_activation_validation','version':195,'status':'PASS' if not failed else 'FAIL','checks':checks,'failed':failed,'enum':{name:i+1 for i,name in enumerate(names)},'attack_helper':'0x144DC','attack_animation_code':'0x0D'}
    if a.out: Path(a.out).write_text(json.dumps(out,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps(out,indent=2,sort_keys=True)); return 1 if failed else 0
if __name__=='__main__': sys.exit(main())
