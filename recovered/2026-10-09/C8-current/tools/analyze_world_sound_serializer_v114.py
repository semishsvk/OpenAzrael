#!/usr/bin/env python3
from pathlib import Path
import argparse, collections, hashlib, json, struct, sys

EXPECTED_EXE='381e4f5c61e4bb8c27f06b1944e6673bbebc39ca219cc08fb9f948da2ca37c00'
EXPECTED_WORLD='f055948e302fa2f6ba364f7ebd3b4bc45f20ef4445af4946c63e4e313a084ae9'
ALLOC=0x20C00
READ_LIKE=0x260D7
WRITE_LIKE=0x30AED

READER_TOP_CALL=0x369DC; READER_TOP=0x29E98; READER_NODE_CALL=0x29EEA; READER_NODE=0x29CF4; READER_BLOB_CALL=0x29D2E; READER_BLOB=0x29638
WRITER_TOP_CALL=0x3661A; WRITER_TOP=0x29E40; WRITER_NODE_CALL=0x29E87; WRITER_NODE=0x29D74; WRITER_BLOB_CALL=0x29DA5; WRITER_BLOB=0x2972C
HANDLER=0x191E9

def sha(b): return hashlib.sha256(b).hexdigest()
def u16(b,o): return struct.unpack_from('<H',b,o)[0]
def call_target(buf,site):
    if site<0 or site+5>len(buf) or buf[site]!=0xE8: return None
    return site+5+int.from_bytes(buf[site+1:site+5],'little',signed=True)
def direct_refs(buf,target):
    return [i for i in range(len(buf)-4) if buf[i]==0xE8 and call_target(buf,i)==target]
def ctoken(buf,start):
    e=buf.find(b'\0',start)
    if e<=start: return None
    s=buf[start:e]
    if not all(0x20<=x<0x7f for x in s): return None
    return s.decode('ascii')

def parse_sound_rows(data):
    off=30
    def take(n):
        nonlocal off
        if off+n>len(data): raise ValueError(f'WORLD overrun at {off:#x} size={n}')
        s=off; b=data[off:off+n]; off+=n; return s,b
    def U():
        s,b=take(2); return s,struct.unpack('<H',b)[0]
    _,n0=U()
    for _ in range(n0): _,n=U(); take(2*n); take(2+2+1+2+1+2+11+30)
    _,n1=U()
    for _ in range(n1): take(2+2+11); _,n=U(); take(2*n)
    _,n2=U()
    for _ in range(n2): take(9); _,n=U(); take(2*n); _,n=U(); take(2*n)
    _,n3=U()
    for _ in range(n3): take(4); _,n=U(); take(2*n)
    U(); U(); _,n6=U(); rows=[]; all27=0; all37=0
    for ti in range(n6):
        _,tf=U(); _,nc=U()
        for ni in range(nc):
            _,oc=U()
            for oi in range(oc):
                _,of=U(); _,c37=U(); all37+=c37; take(37*c37); _,c27=U(); all27+=c27
                for bi in range(c27):
                    pos,raw=take(27)
                    if raw and raw[0]==0x28:
                        token=ctoken(raw,1)
                        if token:
                            end=1+len(token)
                            rows.append({
                              'offset':pos,'token':token,
                              'object_index':u16(raw,13),'room_id':u16(raw,15),
                              'stem_remainder':raw[end+1:13],
                              'tail':raw[17:27]
                            })
    return rows,off,all37,all27

def immediate_27_allocs(o1):
    out=[]
    for i in range(len(o1)-20):
        if o1[i:i+5] != b'\xb8\x1b\x00\x00\x00': continue
        for j in range(i+5,min(i+25,len(o1)-4)):
            if o1[j]==0xE8 and call_target(o1,j)==ALLOC:
                out.append({'mov_site':i,'call_site':j})
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--exe',required=True); ap.add_argument('--world',required=True); ap.add_argument('--out',required=True)
    a=ap.parse_args()
    sys.path.insert(0,str(Path(__file__).resolve().parent))
    from audit_file_open_families_v103 import build_objects
    exe=Path(a.exe).read_bytes(); world=Path(a.world).read_bytes(); o1=build_objects(exe)[0]['virtual']
    rows,eof,n37,n27=parse_sound_rows(world)
    alloc27=immediate_27_allocs(o1)

    groups=collections.defaultdict(list)
    for r in rows: groups[(r['token'].lower(),r['object_index'],r['room_id'])].append(r)
    dup={k:v for k,v in groups.items() if len(v)>1}
    varying_tail={k:v for k,v in dup.items() if len({x['tail'] for x in v})>1}
    varying_stem_remainder={k:v for k,v in dup.items() if len({x['stem_remainder'] for x in v})>1}
    tails=[r['tail'] for r in rows]
    group_summary=[]
    for (tok,obj,room),rs in sorted(dup.items()):
        group_summary.append({
          'token':tok,'section0_index':obj,'room_id':room,'records':len(rs),
          'unique_tail_17_26':len({x['tail'] for x in rs}),
          'unique_unused_stem_storage_remainders':len({x['stem_remainder'] for x in rs})
        })

    checks={
      'exe_hash':sha(exe)==EXPECTED_EXE,
      'world_hash':sha(world)==EXPECTED_WORLD,
      'world_exact_eof':eof==len(world)==96425,
      'sound_rows_44':len(rows)==44,
      'reader_top_edge':call_target(o1,READER_TOP_CALL)==READER_TOP,
      'reader_node_edge':call_target(o1,READER_NODE_CALL)==READER_NODE,
      'reader_blob_edge':call_target(o1,READER_BLOB_CALL)==READER_BLOB,
      'writer_top_edge':call_target(o1,WRITER_TOP_CALL)==WRITER_TOP,
      'writer_node_edge':call_target(o1,WRITER_NODE_CALL)==WRITER_NODE,
      'writer_blob_edge':call_target(o1,WRITER_BLOB_CALL)==WRITER_BLOB,
      'reader_37_alloc_size':o1[0x2969c:0x296ab]==bytes.fromhex('b825000000bb01000000ba25000000'),
      'reader_37_alloc':call_target(o1,0x296ab)==ALLOC,
      'reader_37_raw_read':call_target(o1,0x296b4)==READ_LIKE,
      'reader_27_alloc_size':o1[0x29703:0x29712]==bytes.fromhex('b81b000000bb01000000ba1b000000'),
      'reader_27_alloc':call_target(o1,0x29712)==ALLOC,
      'reader_27_raw_read':call_target(o1,0x2971b)==READ_LIKE,
      'writer_37_raw_size':o1[0x2979c:0x297a1]==bytes.fromhex('ba25000000'),
      'writer_37_raw_write':call_target(o1,0x297a1)==WRITE_LIKE,
      'writer_27_pointer_array':o1[0x297f3:0x297f6]==bytes.fromhex('8b4608'),
      'writer_27_raw_size':o1[0x29800:0x29805]==bytes.fromhex('ba1b000000'),
      'writer_27_raw_write':call_target(o1,0x29805)==WRITE_LIKE,
      'reader_chain_unique_direct_refs':direct_refs(o1,READER_TOP)==[READER_TOP_CALL] and direct_refs(o1,READER_NODE)==[READER_NODE_CALL] and direct_refs(o1,READER_BLOB)==[READER_BLOB_CALL],
      'writer_chain_unique_direct_refs':direct_refs(o1,WRITER_TOP)==[WRITER_TOP_CALL] and direct_refs(o1,WRITER_NODE)==[WRITER_NODE_CALL] and direct_refs(o1,WRITER_BLOB)==[WRITER_BLOB_CALL],
      'only_immediate_27_alloc_is_reader':alloc27==[{'mov_site':0x29703,'call_site':0x29712}],
      'opcode28_handler_record_access_prefix':o1[HANDLER:0x19208]==bytes.fromhex('a1883804008b55e8668b00663b420f0f85e2f4ffff668b420d8b1590380400'),
      'duplicate_semantic_groups_7':len(dup)==7,
      'all_duplicate_groups_have_varying_tail':len(varying_tail)==len(dup)==7,
      'all_duplicate_groups_have_varying_unused_stem_remainder':len(varying_stem_remainder)==len(dup)==7,
      'tap_group_12_unique_tails':len({x['tail'] for x in groups[('797tap',1255,2)]})==12,
    }
    bad=[k for k,v in checks.items() if not v]
    if bad: raise SystemExit('v114 invariant failure: '+', '.join(bad))

    out={
      'schema':'openazrael.world_sound_serializer_audit','version':114,'status':'PASS',
      'sources':{'r_exe_sha256':sha(exe),'world_dat_sha256':sha(world)},
      'reader_chain':{
        'top_call_hex':hex(READER_TOP_CALL),'top_reader_hex':hex(READER_TOP),
        'node_call_hex':hex(READER_NODE_CALL),'node_reader_hex':hex(READER_NODE),
        'blob_call_hex':hex(READER_BLOB_CALL),'blob_reader_hex':hex(READER_BLOB),
        'blob37_behavior':'allocate 0x25 and read exactly 0x25 bytes wholesale',
        'blob27_behavior':'allocate 0x1B and read exactly 0x1B bytes wholesale',
        'confidence':'VERIFIED'
      },
      'writer_chain':{
        'top_call_hex':hex(WRITER_TOP_CALL),'top_writer_hex':hex(WRITER_TOP),
        'node_call_hex':hex(WRITER_NODE_CALL),'node_writer_hex':hex(WRITER_NODE),
        'blob_call_hex':hex(WRITER_BLOB_CALL),'blob_writer_hex':hex(WRITER_BLOB),
        'blob37_behavior':'write exactly 0x25 bytes wholesale',
        'blob27_behavior':'load pointer from second list at +0x08 and write exactly 0x1B bytes wholesale',
        'confidence':'VERIFIED'
      },
      'opaque_serializer_conclusion':{
        'record27':'The matched reader/writer pair treats the complete 27-byte record as an opaque fixed-size memory blob. The serializer does not decode or independently construct fields +13/+15/+17..+26.',
        'record37':'The sibling 37-byte list is likewise serialized wholesale.',
        'producer_boundary':'This closes serializer behavior, not the upstream authoring constructor. The complete PUZZLES/ROOMS -> WORLD producer/compiler remains HOLD.',
        'confidence':'VERIFIED for serialization behavior'
      },
      'allocation_audit':{
        'class':'direct mov eax,0x1B followed by direct call to allocator 0x20C00 within 24 bytes',
        'matches':[{'mov_site_hex':hex(x['mov_site']),'call_site_hex':hex(x['call_site'])} for x in alloc27],
        'finding':'The only match in object1 is the WORLD 27-byte reader allocation at 0x29703/0x29712.',
        'boundary':'This does not exclude constructors that use variable sizes, alternate allocators, stack/static storage, copying, or external authoring code.'
      },
      'opcode28_residue_audit':{
        'sound_records':len(rows),'all_section6_blob27_records':n27,'all_section6_blob37_records':n37,
        'unique_tail_17_26':len(set(tails)),'zero_tail_17_26':sum(t==b'\0'*10 for t in tails),'nonzero_tail_17_26':sum(t!=b'\0'*10 for t in tails),
        'duplicate_semantic_binding_groups':len(dup),'duplicate_groups_with_varying_tail':len(varying_tail),
        'duplicate_groups_with_varying_unused_stem_storage_remainder':len(varying_stem_remainder),
        'tapframe_797tap_records':len(groups[('797tap',1255,2)]),'tapframe_797tap_unique_tails':len({x['tail'] for x in groups[('797tap',1255,2)]}),
        'duplicate_group_summary':group_summary,
        'interpretation':'Bytes outside the runtime-consumed opcode-0x28 fields are not stable even across records with the same sound stem, section-0 object index and room id. Together with the opaque serializer and handler non-use, they must remain residue/UNKNOWN for opcode 0x28 rather than being promoted to gameplay parameters.',
        'confidence':'VERIFIED for variability and non-use by the opcode-0x28 handler; exact origin/meaning remains HOLD.'
      },
      'next_target':'Search constructors/mutators/copy paths for writes into 27-byte action records, especially offsets +17..+26. Do not infer semantics from serialized residue alone.',
      'checks':checks
    }
    Path(a.out).write_text(json.dumps(out,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps({'status':'PASS','checks':len(checks),'sound_records':len(rows),'unique_tails':len(set(tails)),'duplicate_groups':len(dup),'varying_tail_groups':len(varying_tail),'immediate_27_alloc_matches':len(alloc27)},indent=2))

if __name__=='__main__': main()
