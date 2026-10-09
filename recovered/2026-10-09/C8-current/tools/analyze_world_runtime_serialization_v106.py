#!/usr/bin/env python3
"""OpenAzrael v106: close the runtime WORLD.DAT serialization path.

After v103-v105 excluded the obvious direct runtime-open routes for
PUZZLES.DAT, this audit tests the alternative hypothesis conservatively:
R.EXE directly opens WORLD.DAT and deserializes a structured runtime object
store.  It reconstructs the serialization grammar far enough to consume the
bound WORLD.DAT byte-for-byte to EOF, and checks paired reader/writer helpers
in R.EXE.

This does *not* prove that PUZZLES.DAT or ROOMS.DAT are the authoring inputs
used to generate WORLD.DAT.  That transformation remains a separate claim.
"""
from pathlib import Path
import argparse, hashlib, json, struct, sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_file_open_families_v103 import (
    EXPECTED_EXE_SHA256, build_objects, late_string, FOPEN_WRAPPER,
)

EXPECTED_WORLD_SHA256 = "f055948e302fa2f6ba364f7ebd3b4bc45f20ef4445af4946c63e4e313a084ae9"
EXPECTED_PUZZLES_SHA256 = "b8131cf823edb184f04740d5af0a457f4d684e7b0be654b529ec7cdfde1739d1"
READ_LIKE = 0x260D7
WRITE_LIKE = 0x30AED
ALLOC = 0x20C00
WORLD_LOADER = 0x36638
WORLD_OPEN_CALL = 0x36649
WORLD_HEADER_READ_CALL = 0x3665E
WORLD_CLOSE_CALL = 0x3662D

# Seven top-level count-bearing sections, in loader order.  Sections 4 and 5
# allocate zeroed u16 runtime arrays but have no per-record stream parser at
# load time.
SECTION_CODE = [
    dict(index=0, count_global=0x43894, array_global=0x43890, count_read_call=0x36674,
         alloc_size=0x5D, alloc_imm=0x366D7, alloc_call=0x366DC, parser=0x28FCC, parser_call=0x366C9,
         writer=0x28F20),
    dict(index=1, count_global=0x438E0, array_global=0x438E4, count_read_call=0x36706,
         alloc_size=0x15, alloc_imm=0x3675B, alloc_call=0x36760, parser=0x35C50, parser_call=0x3674D,
         writer=0x35CA0),
    dict(index=2, count_global=0x43884, array_global=0x43880, count_read_call=0x3678E,
         alloc_size=0x17, alloc_imm=0x367E9, alloc_call=0x367EE, parser=0x27E2C, parser_call=0x367DB,
         writer=0x27DFA),
    dict(index=3, count_global=0x438E8, array_global=0x438EC, count_read_call=0x36830,
         alloc_size=0x12, alloc_imm=0x3688A, alloc_call=0x3688F, parser=0x35D88, parser_call=0x3687C,
         writer=0x35DC4),
    dict(index=4, count_global=0x438A0, array_global=0x438A4, count_read_call=0x368CC,
         alloc_size=None, parser=None, runtime_zero_u16_array=True),
    dict(index=5, count_global=0x438A8, array_global=0x438AC, count_read_call=0x3692B,
         alloc_size=None, parser=None, runtime_zero_u16_array=True),
    dict(index=6, count_global=0x43898, array_global=0x4389C, count_read_call=0x3698A,
         alloc_size=0x08, alloc_imm=0x369EE, alloc_call=0x369F3, parser=0x29E98, parser_call=0x369DC,
         writer=0x29E40),
]
EXPECTED_COUNTS = [1303, 12, 37, 3, 101, 8, 15]
EXPECTED_WORLD_TIMESTAMP = b"Tue Feb  6 17:27:37 1996\n\0"


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def call_target(buf: bytes, site: int):
    if site < 0 or site + 5 > len(buf) or buf[site] != 0xE8:
        return None
    rel = int.from_bytes(buf[site+1:site+5], 'little', signed=True)
    return site + 5 + rel


def u32le(buf: bytes, off: int):
    return struct.unpack_from('<I', buf, off)[0]


def imm_mov_eax(buf: bytes, off: int):
    if buf[off] != 0xB8:
        return None
    return u32le(buf, off+1)


class Reader:
    def __init__(self, data: bytes):
        self.data = data
        self.off = 0
        self.max_off = 0
    def take(self, n: int) -> bytes:
        if n < 0 or self.off + n > len(self.data):
            raise ValueError(f"WORLD parse overrun at {self.off:#x} requesting {n}")
        out = self.data[self.off:self.off+n]
        self.off += n
        self.max_off = max(self.max_off, self.off)
        return out
    def u16(self) -> int:
        return struct.unpack('<H', self.take(2))[0]
    def dyn_u16(self):
        n = self.u16()
        vals = [self.u16() for _ in range(n)]
        return vals


def cfield(raw: bytes) -> str:
    return raw.split(b'\0', 1)[0].decode('latin1', errors='replace')


def parse_world(data: bytes):
    r = Reader(data)
    header = r.take(30)
    sections = []

    # Section 0: dynamic u16 list + fixed serialized fields written/read by
    # 0x28F20/0x28FCC.  The in-memory object is 0x5D bytes, but serialized
    # runtime-only holes are omitted.
    n0 = r.u16(); names=[]; descriptions=[]; list_elems0=0
    for _ in range(n0):
        ids = r.dyn_u16(); list_elems0 += len(ids)
        r.take(2)  # runtime +06
        r.take(2)  # +08
        r.take(1)  # +0A
        r.take(2)  # +0B
        r.take(1)  # +0D
        r.take(2)  # +0E
        names.append(cfield(r.take(11)))       # +34
        descriptions.append(cfield(r.take(30)))# +3F
    sections.append({'index':0,'count':n0,'end_offset':r.off,'dynamic_u16_elements':list_elems0})

    # Section 1: two u16 + 11 bytes + dynamic u16 list (0x35C50).
    n1 = r.u16(); list_elems1=0
    for _ in range(n1):
        r.take(2); r.take(2); r.take(11)
        list_elems1 += len(r.dyn_u16())
    sections.append({'index':1,'count':n1,'end_offset':r.off,'dynamic_u16_elements':list_elems1})

    # Section 2: 9 fixed bytes + two dynamic u16 lists (0x27E2C).
    n2 = r.u16(); list_a=list_b=0
    for _ in range(n2):
        r.take(9)
        list_a += len(r.dyn_u16())
        list_b += len(r.dyn_u16())
    sections.append({'index':2,'count':n2,'end_offset':r.off,'dynamic_u16_elements_a':list_a,'dynamic_u16_elements_b':list_b})

    # Section 3: two u16 + one dynamic u16 list (0x35D88).
    n3 = r.u16(); list_elems3=0
    for _ in range(n3):
        r.take(2); r.take(2)
        list_elems3 += len(r.dyn_u16())
    sections.append({'index':3,'count':n3,'end_offset':r.off,'dynamic_u16_elements':list_elems3})

    # Sections 4 and 5 are counts only in the stream at this point.  Loader
    # creates zeroed runtime u16 arrays of those lengths.
    n4 = r.u16(); sections.append({'index':4,'count':n4,'end_offset':r.off,'stream_records':0})
    n5 = r.u16(); sections.append({'index':5,'count':n5,'end_offset':r.off,'stream_records':0})

    # Section 6 (0x29E98): u16 field + count of 6-byte list nodes.  Each node
    # (0x29CF4) contains a count of 0x0E-byte runtime objects.  Each such object
    # is deserialized by 0x29638: u16 + count*37-byte blobs + count*27-byte blobs.
    n6 = r.u16(); node_count=0; object_count=0; blobs37=0; blobs27=0
    for _ in range(n6):
        r.take(2)
        nodes = r.u16(); node_count += nodes
        for _ in range(nodes):
            objs = r.u16(); object_count += objs
            for _ in range(objs):
                r.take(2)
                c37 = r.u16(); blobs37 += c37; r.take(37*c37)
                c27 = r.u16(); blobs27 += c27; r.take(27*c27)
    sections.append({'index':6,'count':n6,'end_offset':r.off,'node_count':node_count,
                     'nested_object_count':object_count,'blob37_count':blobs37,'blob27_count':blobs27})

    return {
        'header_hex': header.hex(),
        'header_ascii_prefix': cfield(header),
        'sections': sections,
        'section_counts': [x['count'] for x in sections],
        'end_offset': r.off,
        'file_size': len(data),
        'consumed_exactly_to_eof': r.off == len(data),
        'section0_sample_names': names[:12],
        'section0_sample_descriptions': descriptions[:12],
        'section0_nonempty_names': sum(bool(x) for x in names),
        'section0_nonempty_descriptions': sum(bool(x) for x in descriptions),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--exe', required=True)
    ap.add_argument('--world', required=True)
    ap.add_argument('--puzzles', required=True)
    ap.add_argument('--puzzles-v97', required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    exe = Path(args.exe).read_bytes()
    world = Path(args.world).read_bytes()
    puzzles = Path(args.puzzles).read_bytes()
    v97 = json.loads(Path(args.puzzles_v97).read_text(encoding='utf-8'))
    objs = build_objects(exe)
    o1 = objs[0]['virtual']; o2 = objs[1]['page_span']
    parsed = parse_world(world)

    # Exact 32-byte action blocks from the unbiased v97 population.  Their
    # absence in WORLD establishes that any authoring->WORLD relationship is
    # not a bytewise concatenation/copy of the recovered action slots.
    action_blocks=[]
    for rec in v97['records']:
        a = int(rec['action_offset'])
        b = puzzles[a:a+32]
        if len(b) != 32:
            raise SystemExit(f'v97 action block outside PUZZLES at {a:#x}')
        action_blocks.append(b)
    unique_blocks = set(action_blocks)
    exact_world_hits = sorted(world.find(b) for b in unique_blocks if world.find(b) >= 0)

    section_checks=[]
    for s in SECTION_CODE:
        item={
            'index':s['index'],
            'count_global_hex':hex(s['count_global']),
            'array_global_hex':hex(s['array_global']),
            'count_read_call_hex':hex(s['count_read_call']),
            'count_read_target_hex':hex(call_target(o1,s['count_read_call'])) if call_target(o1,s['count_read_call']) is not None else None,
            'alloc_size':s.get('alloc_size'),
            'parser_hex':hex(s['parser']) if s.get('parser') is not None else None,
            'writer_hex':hex(s['writer']) if s.get('writer') is not None else None,
        }
        if s.get('alloc_size') is not None:
            item['alloc_immediate_seen']=imm_mov_eax(o1,s['alloc_imm'])
            item['alloc_call_target_hex']=hex(call_target(o1,s['alloc_call']))
            item['parser_call_target_hex']=hex(call_target(o1,s['parser_call']))
        else:
            item['runtime_zero_u16_array']=True
        section_checks.append(item)

    checks = {
        'exe_sha256': sha256(exe) == EXPECTED_EXE_SHA256,
        'world_sha256': sha256(world) == EXPECTED_WORLD_SHA256,
        'puzzles_sha256': sha256(puzzles) == EXPECTED_PUZZLES_SHA256,
        'world_rb_string': late_string(o2,0x3BA5) == 'rb',
        'world_filename_string': late_string(o2,0x3BA8) == 'world.dat',
        'world_open_targets_fopen': call_target(o1,WORLD_OPEN_CALL) == FOPEN_WRAPPER,
        'world_header_read_targets_read': call_target(o1,WORLD_HEADER_READ_CALL) == READ_LIKE,
        'world_header_read_size_30': o1[0x36650:0x3665A] == bytes.fromhex('bb01000000 ba1e000000'.replace(' ','')),
        'world_close_targets_close_wrapper': call_target(o1,WORLD_CLOSE_CALL) == 0x262A1,
        'world_embedded_timestamp_exact': world.startswith(EXPECTED_WORLD_TIMESTAMP),
        'world_sections_count_exact': parsed['section_counts'] == EXPECTED_COUNTS,
        'world_parser_consumes_exact_eof': parsed['consumed_exactly_to_eof'],
        'world_parser_eof_offset_exact': parsed['end_offset'] == 96425,
        'all_section_count_reads_target_read': all(call_target(o1,s['count_read_call']) == READ_LIKE for s in SECTION_CODE),
        'all_alloc_sizes_and_targets_match': all(
            (s.get('alloc_size') is None) or
            (imm_mov_eax(o1,s['alloc_imm']) == s['alloc_size'] and call_target(o1,s['alloc_call']) == ALLOC)
            for s in SECTION_CODE
        ),
        'all_record_parsers_match': all(
            (s.get('parser') is None) or call_target(o1,s['parser_call']) == s['parser']
            for s in SECTION_CODE
        ),
        'section0_reader_uses_dyn_list': call_target(o1,0x28FD4) == 0x36058,
        'section0_writer_uses_dyn_list_writer': call_target(o1,0x28F28) == 0x36004,
        'dyn_list_reader_reads_count_and_elements': call_target(o1,0x36074) == READ_LIKE and call_target(o1,0x360A4) == READ_LIKE,
        'dyn_list_writer_writes_count_and_elements': call_target(o1,0x3601D) == WRITE_LIKE and call_target(o1,0x36048) == WRITE_LIKE,
        'section6_nested_parser_edge': call_target(o1,0x29EEA) == 0x29CF4,
        'nested_object_parser_edge': call_target(o1,0x29D2E) == 0x29638,
        'puzzles_v97_population_224': v97.get('population') == 224 and len(action_blocks) == 224,
        'puzzles_unique_action_blocks_133': len(unique_blocks) == 133,
        'no_exact_32byte_puzzles_action_block_in_world': len(exact_world_hits) == 0,
    }
    bad=[k for k,v in checks.items() if not v]
    if bad:
        raise SystemExit('v106 invariant failure: '+', '.join(bad)+f' parsed={parsed["section_counts"]} eof={parsed["end_offset"]}')

    out={
        'schema':'openazrael.world_runtime_serialization',
        'version':106,
        'status':'PASS',
        'sources':{
            'r_exe_sha256':sha256(exe),
            'world_dat_sha256':sha256(world),
            'puzzles_dat_sha256':sha256(puzzles),
        },
        'runtime_open':{
            'loader_object1_offset_hex':hex(WORLD_LOADER),
            'open_call_hex':hex(WORLD_OPEN_CALL),
            'mode':'rb','filename':'world.dat',
            'header_read_call_hex':hex(WORLD_HEADER_READ_CALL),
            'header_read_bytes':30,
            'close_call_hex':hex(WORLD_CLOSE_CALL),
            'confidence':'VERIFIED',
        },
        'world_serialization':parsed,
        'loader_sections':section_checks,
        'reader_writer_pairs':{
            'section0':{'reader':'0x28fcc','writer':'0x28f20','dynamic_u16_reader':'0x36058','dynamic_u16_writer':'0x36004'},
            'section1':{'reader':'0x35c50','writer':'0x35ca0'},
            'section2':{'reader':'0x27e2c','writer':'0x27dfa'},
            'section3':{'reader':'0x35d88','writer':'0x35dc4'},
            'section6':{'reader':'0x29e98','writer':'0x29e40','node_reader':'0x29cf4','nested_object_reader':'0x29638'},
            'finding':'Multiple matched reader/writer pairs plus exact EOF consumption identify WORLD.DAT as a structured runtime serialization/object database, not an opaque blob.',
            'confidence':'HIGH',
        },
        'puzzles_relationship_adversarial_check':{
            'v97_action_records':len(action_blocks),
            'unique_32byte_action_blocks':len(unique_blocks),
            'exact_unique_blocks_found_in_world':len(exact_world_hits),
            'finding':'None of the 133 unique recovered 32-byte PUZZLES action blocks is copied byte-for-byte into WORLD.DAT. If PUZZLES contributes to WORLD, the relationship is transformed/compiled rather than raw concatenation.',
            'confidence':'VERIFIED for absence; HOLD for transformation identity',
        },
        'conclusion':{
            'world_runtime_loaded':'VERIFIED',
            'world_structured_runtime_serialization':'HIGH',
            'puzzles_rooms_are_authoring_inputs_to_world':'PROBABLE/HOLD',
            'important_boundary':'v106 does not prove a PUZZLES.DAT -> WORLD.DAT compiler edge. It proves the WORLD runtime loader/serialization and excludes raw 32-byte PUZZLES action-block copying.',
            'next_step':'Trace the WORLD writer/callers and compare its input object families against PUZZLES/ROOMS structures to identify an authoring/export path, or find runtime code that resolves PUZZLES-derived event identities inside WORLD objects.',
        },
        'checks':checks,
    }
    Path(args.out).write_text(json.dumps(out,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print('PASS v106: WORLD sections', parsed['section_counts'], 'EOF', parsed['end_offset'], '/', len(world), 'PUZZLES exact blocks in WORLD', len(exact_world_hits))

if __name__ == '__main__':
    main()
