#!/usr/bin/env python3
"""OpenAzrael v107: trace WORLD writer reachability and the PUZZLES->WORLD sound-action bridge.

v106 proved that the demo R.EXE directly loads WORLD.DAT and that WORLD is a
structured runtime serialization.  Its proposed next step was to follow the
paired WORLD writer.  v107 first tests that premise adversarially, then pivots
to a byte-structural correlation between recovered PUZZLES action records and
WORLD section-6 27-byte blobs.

Evidence boundaries:
- Exact byte/control-flow/record correspondences reported here are VERIFIED.
- A compiler/authoring edge from PUZZLES into WORLD is HIGH when supported by
  the systematic action correspondence, but the complete producer pipeline is
  not claimed VERIFIED.
- Absence of direct CALL/JMP/fixup references does not prove runtime
  unreachability through every possible computed/indirect mechanism.
"""
from pathlib import Path
import argparse, collections, hashlib, json, struct, sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_file_open_families_v103 import EXPECTED_EXE_SHA256, build_objects, late_string, FOPEN_WRAPPER
from analyze_world_runtime_serialization_v106 import (
    EXPECTED_WORLD_SHA256, EXPECTED_PUZZLES_SHA256, parse_world
)

WORLD_WRITER = 0x364A8
WORLD_WRITER_OPEN_CALL = 0x364B9
WORLD_READER = 0x36638
WORLD_READER_DIRECT_CALL = 0x1AAED
WORLD_INIT_ROUTINE = 0x1AA78
WORLD_INIT_DIRECT_CALL = 0x349E
SGDNAME_LOADER = 0x36414
SGDNAME_OPEN_CALL = 0x36423


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def rel32_target(buf: bytes, site: int, opcode: int):
    if site < 0 or site + 5 > len(buf) or buf[site] != opcode:
        return None
    return site + 5 + int.from_bytes(buf[site+1:site+5], 'little', signed=True)


def rel32_refs(buf: bytes, target: int, opcode: int):
    return [i for i in range(0, len(buf)-4) if buf[i] == opcode and rel32_target(buf, i, opcode) == target]


def parse_section6_blobs(data: bytes):
    """Re-walk the v106 WORLD grammar and retain section-6 blob boundaries."""
    off = 0
    def take(n):
        nonlocal off
        if n < 0 or off + n > len(data):
            raise ValueError(f'WORLD overrun at {off:#x}, n={n}')
        start = off
        b = data[off:off+n]
        off += n
        return start, b
    def u16():
        start, b = take(2)
        return start, struct.unpack('<H', b)[0]

    take(30)
    _, n0 = u16()
    for _ in range(n0):
        _, n = u16(); take(2*n); take(2+2+1+2+1+2+11+30)
    _, n1 = u16()
    for _ in range(n1):
        take(2+2+11); _, n = u16(); take(2*n)
    _, n2 = u16()
    for _ in range(n2):
        take(9); _, n = u16(); take(2*n); _, n = u16(); take(2*n)
    _, n3 = u16()
    for _ in range(n3):
        take(4); _, n = u16(); take(2*n)
    u16(); u16()

    _, n6 = u16()
    blobs = []
    for top_index in range(n6):
        _, top_field = u16()
        _, node_count = u16()
        for node_index in range(node_count):
            _, object_count = u16()
            for object_index in range(object_count):
                _, object_field = u16()
                _, count37 = u16()
                for blob_index in range(count37):
                    start, raw = take(37)
                    blobs.append({
                        'kind':'blob37','offset':start,'size':37,'raw':raw,
                        'top_index':top_index,'node_index':node_index,
                        'object_index':object_index,'blob_index':blob_index,
                        'top_field':top_field,'object_field':object_field,
                    })
                _, count27 = u16()
                for blob_index in range(count27):
                    start, raw = take(27)
                    blobs.append({
                        'kind':'blob27','offset':start,'size':27,'raw':raw,
                        'top_index':top_index,'node_index':node_index,
                        'object_index':object_index,'blob_index':blob_index,
                        'top_field':top_field,'object_field':object_field,
                    })
    return {'top_count':n6,'end_offset':off,'blobs':blobs}


def printable_c_token(buf: bytes, start: int):
    end = buf.find(b'\0', start)
    if end < 0 or end == start:
        return None
    raw = buf[start:end]
    if not all(0x20 <= b <= 0x7E for b in raw):
        return None
    try:
        return raw.decode('ascii')
    except UnicodeDecodeError:
        return None


def counter_dict(c):
    return {k:c[k] for k in sorted(c)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--exe', required=True)
    ap.add_argument('--world', required=True)
    ap.add_argument('--puzzles', required=True)
    ap.add_argument('--puzzles-v97', required=True)
    ap.add_argument('--canonical-xrefs', required=True)
    ap.add_argument('--demo-dir', required=True, help='Directory containing the demo WAV assets for independent stem validation.')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()

    exe = Path(a.exe).read_bytes()
    world = Path(a.world).read_bytes()
    puzzles = Path(a.puzzles).read_bytes()
    v97 = json.loads(Path(a.puzzles_v97).read_text(encoding='utf-8'))
    xref_doc = json.loads(Path(a.canonical_xrefs).read_text(encoding='utf-8'))
    demo_dir = Path(a.demo_dir)

    objs = build_objects(exe)
    o1 = objs[0]['virtual']; o2 = objs[1]['page_span']
    parsed = parse_world(world)
    sec6 = parse_section6_blobs(world)

    # --- v106 writer-lineage premise: is the paired writer statically referenced? ---
    writer_calls = rel32_refs(o1, WORLD_WRITER, 0xE8)
    writer_jumps = rel32_refs(o1, WORLD_WRITER, 0xE9)
    reader_calls = rel32_refs(o1, WORLD_READER, 0xE8)
    init_calls = rel32_refs(o1, WORLD_INIT_ROUTINE, 0xE8)
    writer_fixups = [x for x in xref_doc.get('xrefs', [])
                     if x.get('target_object') == 1 and x.get('target_offset') == WORLD_WRITER]

    # --- Recover structurally validated PUZZLES opcode 0x28 records from v97. ---
    puzzle_sound = []
    for rec in v97['records']:
        action = int(rec['action_offset'])
        block = puzzles[action:action+32]
        if len(block) != 32 or block[:2] != b'\x10\x00' or block[2] != 0x28:
            continue
        token = printable_c_token(block, 3)
        if token is None:
            continue
        puzzle_sound.append({
            'action_offset': action,
            'action_offset_hex': hex(action),
            'token': token,
            'block_hex': block.hex(),
        })
    puzzle_counts = collections.Counter(x['token'].lower() for x in puzzle_sound)

    # --- Find runtime 27-byte records that themselves begin 0x28 + C-string. ---
    world_sound = []
    for blob in sec6['blobs']:
        raw = blob['raw']
        if blob['kind'] != 'blob27' or not raw or raw[0] != 0x28:
            continue
        token = printable_c_token(raw, 1)
        if token is None:
            continue
        item = {k:v for k,v in blob.items() if k != 'raw'}
        item.update({'offset_hex':hex(blob['offset']),'token':token,'raw_hex':raw.hex()})
        world_sound.append(item)
    world_counts = collections.Counter(x['token'].lower() for x in world_sound)

    shared = puzzle_counts & world_counts
    puzzle_only = puzzle_counts - world_counts
    world_only = world_counts - puzzle_counts
    shared_unique = sorted(set(puzzle_counts) & set(world_counts))
    wav_stems = {p.stem.lower() for p in demo_dir.iterdir() if p.is_file() and p.suffix.lower() == '.wav'}
    all_world_sound_tokens_are_assets = all(t in wav_stems for t in world_counts)

    # Adversarial control: established non-sound demo operation families from
    # v19 should not magically exhibit the same exact opcode+token preservation.
    # Read the v89 record corpus next to v97 when available.
    v89_path = Path(a.puzzles_v97).with_name('puzzles_event_ir_v89.json')
    controls = {}
    if v89_path.exists():
        v89 = json.loads(v89_path.read_text(encoding='utf-8'))
        for opcode in (0x17,0x18,0x19,0x22):
            rows=[r for r in v89.get('records',[]) if int(r.get('legacy_opcode',-1)) == opcode]
            unique=sorted({r['token'] for r in rows})
            matched=[]
            for token in unique:
                pat=bytes([opcode])+token.encode('latin1')+b'\0'
                if world.find(pat) >= 0:
                    matched.append(token)
            controls[hex(opcode)]={
                'record_count':len(rows),'unique_tokens':len(unique),
                'exact_opcode_token_matches_in_world':matched,
            }

    checks = {
        'exe_sha256': sha256(exe) == EXPECTED_EXE_SHA256,
        'world_sha256': sha256(world) == EXPECTED_WORLD_SHA256,
        'puzzles_sha256': sha256(puzzles) == EXPECTED_PUZZLES_SHA256,
        'world_v106_still_exact_eof': parsed['consumed_exactly_to_eof'] and parsed['end_offset'] == len(world) == 96425,
        'world_writer_prologue': o1[WORLD_WRITER:WORLD_WRITER+5] == bytes.fromhex('53 51 52 56 57'),
        'world_writer_mode_wb': late_string(o2,0x3B98) == 'wb',
        'world_writer_filename': late_string(o2,0x3B9B) == 'world.dat',
        'world_writer_open_targets_fopen': rel32_target(o1,WORLD_WRITER_OPEN_CALL,0xE8) == FOPEN_WRAPPER,
        'world_writer_zero_direct_calls': len(writer_calls) == 0,
        'world_writer_zero_direct_jumps': len(writer_jumps) == 0,
        'world_writer_zero_canonical_fixup_refs': len(writer_fixups) == 0,
        'world_reader_single_direct_call': reader_calls == [WORLD_READER_DIRECT_CALL],
        'world_init_single_direct_call': init_calls == [WORLD_INIT_DIRECT_CALL],
        'sgdname_mode_rb': late_string(o2,0x3B88) == 'rb',
        'sgdname_filename': late_string(o2,0x3B8B) == 'SGDNAME.DAT',
        'sgdname_open_targets_fopen': rel32_target(o1,SGDNAME_OPEN_CALL,0xE8) == FOPEN_WRAPPER,
        'section6_exact_eof': sec6['end_offset'] == len(world),
        'puzzles_structural_sound_records_40': len(puzzle_sound) == 40,
        'world_section6_sound_records_44': len(world_sound) == 44,
        'puzzles_sound_unique_tokens_13': len(puzzle_counts) == 13,
        'world_sound_unique_tokens_17': len(world_counts) == 17,
        'shared_multiset_records_38': sum(shared.values()) == 38,
        'all_puzzles_sound_tokens_exist_in_world': set(puzzle_counts) <= set(world_counts),
        'all_world_sound_tokens_resolve_to_demo_wav': all_world_sound_tokens_are_assets,
        'non_sound_control_has_no_exact_opcode_token_matches': all(
            len(v['exact_opcode_token_matches_in_world']) == 0 for v in controls.values()
        ) if controls else True,
    }
    bad=[k for k,v in checks.items() if not v]
    if bad:
        raise SystemExit('v107 invariant failure: '+', '.join(bad))

    out = {
        'schema':'openazrael.world_puzzle_sound_bridge',
        'version':107,
        'status':'PASS',
        'sources':{
            'r_exe_sha256':sha256(exe),
            'world_dat_sha256':sha256(world),
            'puzzles_dat_sha256':sha256(puzzles),
            'puzzles_v97':str(Path(a.puzzles_v97).name),
            'canonical_xrefs':str(Path(a.canonical_xrefs).name),
        },
        'world_writer_static_reachability':{
            'writer_object1_offset_hex':hex(WORLD_WRITER),
            'writer_mode':'wb','writer_filename':'world.dat',
            'direct_call_sites':[hex(x) for x in writer_calls],
            'direct_jmp_sites':[hex(x) for x in writer_jumps],
            'canonical_le_fixup_refs':writer_fixups,
            'finding':'No direct CALL, direct near JMP, or canonical LE fixup reference targets the paired WORLD writer in the bound executable.',
            'confidence':'VERIFIED for audited static reference classes; HOLD for total runtime reachability because computed/indirect invocation is not excluded.',
            'correction':'v106 proposed following WORLD writer callers. v107 finds no caller in the audited static reference classes, so the writer cannot currently establish an authoring/export producer lineage.',
        },
        'world_reader_live_chain':{
            'reader_object1_offset_hex':hex(WORLD_READER),
            'reader_direct_call_sites':[hex(x) for x in reader_calls],
            'enclosing_init_routine_hex':hex(WORLD_INIT_ROUTINE),
            'init_direct_call_sites':[hex(x) for x in init_calls],
            'preceding_sgdname_loader_hex':hex(SGDNAME_LOADER),
            'sequence':'central init path -> SGDNAME.DAT reader -> WORLD.DAT reader',
            'confidence':'HIGH for runtime/startup initialization role; exact original function names remain unknown.',
        },
        'puzzles_opcode_28':{
            'structural_records':len(puzzle_sound),
            'unique_tokens':len(puzzle_counts),
            'token_counts':counter_dict(puzzle_counts),
        },
        'world_section6_opcode_28_blob27':{
            'records':len(world_sound),
            'unique_tokens':len(world_counts),
            'token_counts':counter_dict(world_counts),
            'all_tokens_resolve_to_demo_wav':all_world_sound_tokens_are_assets,
            'records_detail':world_sound,
        },
        'multiset_correspondence':{
            'shared_records':sum(shared.values()),
            'puzzles_records':sum(puzzle_counts.values()),
            'coverage_of_puzzles_records':sum(shared.values())/sum(puzzle_counts.values()),
            'shared_unique_tokens':shared_unique,
            'shared_unique_token_count':len(shared_unique),
            'puzzles_only_counts':counter_dict(puzzle_only),
            'world_only_counts':counter_dict(world_only),
            'finding':'38/40 structurally recovered PUZZLES opcode-0x28 sound actions have a multiset counterpart among WORLD section-6 27-byte records that begin with the same opcode byte and WAV stem. All 13 PUZZLES sound stems occur in WORLD. The two unmatched PUZZLES instances are 995; WORLD has six additional runtime sound records relative to this v97 PUZZLES population.',
            'exact_binary_fact_confidence':'VERIFIED',
            'producer_edge_interpretation':'HIGH: this is direct structural evidence that at least the sound-action identity crosses the authoring/runtime boundary, but it does not reconstruct the complete compiler.',
        },
        'adversarial_non_sound_controls':controls,
        'conclusion':{
            'world_writer_as_producer_trace':'SUPERSEDED/HOLD',
            'puzzles_0x28_to_world_section6_sound_identity':'HIGH',
            'complete_puzzles_to_world_compiler':'HOLD',
            'next_step':'Reverse the WORLD section-6 27-byte sound record fields and its 0x29638/0x29CF4 reader path, then map numeric operands back to PUZZLES target/state operands. This is now a more evidence-rich route than the statically unreferenced WORLD writer.',
        },
        'checks':checks,
    }
    Path(a.out).write_text(json.dumps(out,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps({
        'status':'PASS','checks':len(checks),
        'writer_direct_callers':len(writer_calls),
        'puzzles_sound_records':len(puzzle_sound),
        'world_sound_records':len(world_sound),
        'shared_multiset_records':sum(shared.values()),
        'shared_unique_tokens':len(shared_unique),
        'world_sound_tokens_all_wav':all_world_sound_tokens_are_assets,
    },indent=2))

if __name__ == '__main__':
    main()
