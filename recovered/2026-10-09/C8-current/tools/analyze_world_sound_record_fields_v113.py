#!/usr/bin/env python3
from pathlib import Path
import argparse, hashlib, json, struct, sys

EXPECTED_EXE='381e4f5c61e4bb8c27f06b1944e6673bbebc39ca219cc08fb9f948da2ca37c00'
EXPECTED_WORLD='f055948e302fa2f6ba364f7ebd3b4bc45f20ef4445af4946c63e4e313a084ae9'
EXPECTED_PUZZLES='b8131cf823edb184f04740d5af0a457f4d684e7b0be654b529ec7cdfde1739d1'
DISPATCH_CMP=0x1870B
HANDLER=0x191E9
DYNAMIC_3D_START=0x0D155
SECTION0_ARRAY_GLOBAL=0x43890
SECTION0_COUNT_GLOBAL=0x43894
CURRENT_CONTEXT_GLOBAL=0x43888
SECTION0_LOADER_ARRAY_STORE=0x366A2
SECTION0_READER=0x28FCC
FORMAT_IMM=0x2EF8

def sha(b): return hashlib.sha256(b).hexdigest()
def u16(b,o): return struct.unpack_from('<H',b,o)[0]
def call_target(buf, site):
    if site<0 or site+5>len(buf) or buf[site]!=0xE8: return None
    return site+5+int.from_bytes(buf[site+1:site+5],'little',signed=True)
def ctoken(buf,start):
    e=buf.find(b'\0',start)
    if e<=start: return None
    x=buf[start:e]
    if not all(0x20<=c<0x7f for c in x): return None
    return x.decode('ascii')

def parse_section0(world):
    off=30; n=u16(world,off); off+=2; rows=[]
    for i in range(n):
        cnt=u16(world,off); off+=2
        ids=[u16(world,off+2*j) for j in range(cnt)]; off+=2*cnt
        off+=2+2+1+2+1+2
        name=world[off:off+11].split(b'\0',1)[0].decode('latin1'); off+=11
        desc=world[off:off+30].split(b'\0',1)[0].decode('latin1'); off+=30
        rows.append({'index':i,'name':name,'description':desc,'ids':ids})
    return rows,off

def parse_sec6_sound(world):
    off=30
    def take(n):
        nonlocal off
        s=off; out=world[off:off+n]; off+=n; return s,out
    def U():
        s,b=take(2); return s,struct.unpack('<H',b)[0]
    _,n0=U()
    for _ in range(n0):
        _,n=U(); take(2*n); take(2+2+1+2+1+2+11+30)
    _,n1=U()
    for _ in range(n1): take(2+2+11); _,n=U(); take(2*n)
    _,n2=U()
    for _ in range(n2): take(9); _,n=U(); take(2*n); _,n=U(); take(2*n)
    _,n3=U()
    for _ in range(n3): take(4); _,n=U(); take(2*n)
    U(); U(); _,n6=U(); rows=[]
    for ti in range(n6):
        _,tf=U(); _,nc=U()
        for ni in range(nc):
            _,oc=U()
            for oi in range(oc):
                _,of=U(); _,c37=U(); take(37*c37); _,c27=U()
                for bi in range(c27):
                    start,raw=take(27)
                    if raw and raw[0]==0x28:
                        token=ctoken(raw,1)
                        if token:
                            rows.append({'offset':start,'token':token,'raw':raw,'top_index':ti,'node_index':ni,'object_index':oi,'blob_index':bi,'object_field':of,'top_field':tf})
    return rows,off

def puzzle_sounds(puzzles,v97):
    out=[]
    for rec in v97['records']:
        a=int(rec['action_offset']); b=puzzles[a:a+32]
        if len(b)==32 and b[:3]==b'\x10\x00\x28':
            token=ctoken(b,3)
            if token: out.append({'offset':a,'token':token})
    return out

def lcs_pairs(a,b):
    A=[x['token'].lower() for x in a]; B=[x['token'].lower() for x in b]
    n,m=len(A),len(B); dp=[[0]*(m+1) for _ in range(n+1)]
    for i in range(n-1,-1,-1):
        for j in range(m-1,-1,-1):
            dp[i][j]=1+dp[i+1][j+1] if A[i]==B[j] else max(dp[i+1][j],dp[i][j+1])
    out=[];i=j=0
    while i<n and j<m:
        if A[i]==B[j] and dp[i][j]==1+dp[i+1][j+1]: out.append((i,j));i+=1;j+=1
        elif dp[i+1][j]>=dp[i][j+1]: i+=1
        else:j+=1
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--exe',required=True); ap.add_argument('--world',required=True); ap.add_argument('--puzzles',required=True)
    ap.add_argument('--puzzles-v97',required=True); ap.add_argument('--manifest-dir',required=True); ap.add_argument('--demo-rooms-evidence',required=True); ap.add_argument('--out',required=True)
    a=ap.parse_args()
    # import repository helper only after args parse
    sys.path.insert(0,str(Path(__file__).resolve().parent))
    try:
        from audit_file_open_families_v103 import build_objects, late_string
    except ImportError:
        # local validation path can point PYTHONPATH to project tools
        from audit_file_open_families_v103 import build_objects, late_string
    exe_path=Path(a.exe); world_path=Path(a.world); puzzles_path=Path(a.puzzles); v97_path=Path(a.puzzles_v97); evidence_path=Path(a.demo_rooms_evidence)
    exe=exe_path.read_bytes(); world=world_path.read_bytes(); puzzles=puzzles_path.read_bytes(); v97_bytes=v97_path.read_bytes(); v97=json.loads(v97_bytes)
    objs=build_objects(exe); o1=objs[0]['virtual']; o2=objs[1]['page_span']
    sec0,_=parse_section0(world); W,eof=parse_sec6_sound(world); P=puzzle_sounds(puzzles,v97); pairs=lcs_pairs(P,W)
    manifests={}
    for room in ('R1','R7','R8'):
        mp=Path(a.manifest_dir)/f'{room}.textured.v44.manifest.json'
        mb=mp.read_bytes(); d=json.loads(mb)
        manifests[room]={x['object'].lower() for x in d['objects']}
        manifests.setdefault('_fingerprints',{})[room]={'name':mp.name,'sha256':sha(mb)}
    room_map={0:'R1',1:'R7',2:'R8'}
    aligned=[]; direct=0; unresolved=[]
    for pi,wj in pairs:
        raw=W[wj]['raw']; idx=u16(raw,13); rid=u16(raw,15); obj=sec0[idx]
        room=room_map.get(rid,'UNKNOWN'); direct_match=obj['name'].lower() in manifests.get(room,set())
        if direct_match: direct+=1
        else: unresolved.append({'token':P[pi]['token'],'object_index':idx,'object_name':obj['name'],'room_id':rid})
        aligned.append({'token':P[pi]['token'],'puzzles_offset_hex':hex(P[pi]['offset']),'world_offset_hex':hex(W[wj]['offset']),'section0_index':idx,'section0_name':obj['name'],'section0_description':obj['description'],'room_id':rid,'room':room,'direct_xaf_manifest_match':direct_match})
    # remaining R7 aliases must be independently represented in room evidence
    room_ev_bytes=evidence_path.read_bytes(); room_ev=json.loads(room_ev_bytes); evtxt=json.dumps(room_ev).lower()
    alias_ok=all((x['object_name'].lower()=='well_door' and 'wellroomdoor' in evtxt) or (x['object_name'].lower()=='r7p1' and 'r7demo' in evtxt) for x in unresolved)
    # handler/dispatcher machine invariants
    checks={
      'exe_hash':sha(exe)==EXPECTED_EXE,'world_hash':sha(world)==EXPECTED_WORLD,'puzzles_hash':sha(puzzles)==EXPECTED_PUZZLES,
      'puzzles_sound_40':len(P)==40,'world_sound_44':len(W)==44,'ordered_lcs_38':len(pairs)==38,'world_exact_eof':eof==len(world),
      'dispatcher_reads_opcode_and_bounds_28':o1[DISPATCH_CMP:DISPATCH_CMP+6]==bytes.fromhex('8a003c280f87'),
      'dispatcher_preserves_payload_pointer_at_plus1':o1[0x18715:0x1871e]==bytes.fromhex('8b4de825ff00000041'),
      'handler_current_context_compare_plus15':o1[0x191e9:0x191fc].find(bytes.fromhex('663b420f'))>=0,
      'handler_loads_section0_index_plus13':o1[0x191fe:0x19202]==bytes.fromhex('668b420d'),
      'handler_uses_section0_array_global':o1[0x19202:0x19208]==bytes.fromhex('8b1590380400'),
      'section0_loader_stores_same_array_global':o1[SECTION0_LOADER_ARRAY_STORE:SECTION0_LOADER_ARRAY_STORE+5]==bytes.fromhex('a390380400'),
      'handler_uses_object_name_plus34':o1[0x1920d:0x19213]==bytes.fromhex('8b048283c034'),
      'handler_pushes_record_plus1_for_filename':o1[0x19226]==0x51,
      'wav_format_string':late_string(o2,FORMAT_IMM)=='%s.WAV',
      'handler_calls_dynamic_3d_start':call_target(o1,0x19252)==DYNAMIC_3D_START,
      'section0_reader_name_field_11_bytes':o1[0x29050:0x2905f]==bytes.fromhex('ba0b0000008d473489f1e878d0ffff'),
      'direct_manifest_room_matches_35':direct==35,
      'remaining_three_are_r7_aliases':len(unresolved)==3 and alias_ok,
    }
    bad=[k for k,v in checks.items() if not v]
    if bad: raise SystemExit('v113 invariant failure: '+', '.join(bad))
    ponly=[P[i]['token'] for i in range(len(P)) if i not in {x for x,_ in pairs}]
    wonly=[W[j]['token'] for j in range(len(W)) if j not in {y for _,y in pairs}]
    referenced=sorted({x['section0_index'] for x in aligned})
    compact_objects=[{'index':i,'name':sec0[i]['name'],'description':sec0[i]['description']} for i in referenced]
    out={
      'schema':'openazrael.world_sound_record_fields','version':113,'status':'PASS',
      'sources':{
        'r_exe_sha256':sha(exe),'world_dat_sha256':sha(world),'puzzles_dat_sha256':sha(puzzles),
        'puzzles_v97':{'name':v97_path.name,'sha256':sha(v97_bytes)},
        'room_manifests':manifests['_fingerprints'],
        'demo_rooms_evidence':{'name':evidence_path.name,'sha256':sha(room_ev_bytes)},
        'note':'Original/commercial payloads and full derived manifests remain outside the source-safe Git boundary; only fingerprints and compact evidence are emitted.'
      },
      'ordered_correspondence':{'puzzles_records':len(P),'world_records':len(W),'lcs_matches':len(pairs),'puzzles_only_tokens':ponly,'world_only_tokens':wonly,'confidence':'VERIFIED'},
      'record_layout':{
        'size':27,
        'opcode':{'offset':0,'size':1,'value':40,'meaning':'sound action opcode','confidence':'VERIFIED'},
        'sound_stem':{'offset':1,'encoding':'NUL-terminated ASCII within pre-field area','runtime_use':'record+1 is passed to sprintf-style %s.WAV formatting','confidence':'VERIFIED'},
        'section0_object_index':{'offset':13,'size':2,'endian':'little','runtime_use':'indexes WORLD section-0 pointer array at global 0x43890','confidence':'VERIFIED'},
        'room_id':{'offset':15,'size':2,'endian':'little','runtime_use':'compared against current runtime context/room word via global 0x43888','mapping':{'0':'R1','1':'R7','2':'R8'},'direct_xaf_manifest_matches':direct,'remaining_alias_matches':len(unresolved),'confidence':'VERIFIED for demo corpur'},
        'tail_17_26':{'offset':17,'size':10,'runtime_use':'not read by the opcode-0x28 handler path 0x191E9..0x19257','meaning':'UNKNOWN/HOLD'}
      },
      'spatial_playback_chain':{
        'handler_object1_offset_hex':hex(HANDLER),'handler_linear_hex':hex(0x10000+HANDLER),'section0_array_global_hex':hex(SECTION0_ARRAY_GLOBAL),'current_context_global_hex':hex(CURRENT_CONTEXT_GLOBAL),
        'section0_name_runtime_offset_hex':'0x34','section0_name_serialized_size':11,'filename_format':'%s.WAV','dynamic_3d_start_object1_offset_hex':hex(DYNAMIC_3D_START),
        'finding':'Opcode 0x28 filters by room id, resolves a section-0 object index, uses that object name to resolve a live scene object/spatial position, formats record+1 as <stem>.WAV, and calls the dynamic 3D sample start routine.',
        'confidence':'VERIFIED for control/data flow; existing v42 role identity of 0xD155 is HIGH.'
      },
      'referenced_section0_objects':compact_objects,
      'ordered_alignment':[{'token':x['token'],'section0_index':x['section0_index'],'section0_name':x['section0_name'],'room_id':x['room_id'],'direct_xaf_manifest_match':x['direct_xaf_manifest_match']} for x in aligned],
      'remaining_field_boundary':'No meaning is assigned to bytes +17..+26. The 0x28 handler does not consume them; they remain UNKNOWN/HOLD.',
      'compiler_boundary':'The field-level runtime bridge is recovered for opcode 0x28, but the complete PUZZLES/ROOMS -> WORLD producer/compiler remains HOLD.',
      'checks':checks
    }
    Path(a.out).write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'status':'PASS','ordered_matches':len(pairs),'direct_room_matches':direct,'alias_room_matches':len(unresolved),'section0_objects':len(referenced),'checks':len(checks)},indent=2))
if __name__=='__main__': main()
