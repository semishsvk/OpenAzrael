#!/usr/bin/env python3
"""OpenAzrael v103: exhaustive direct stdio-open census for the bound demo R.EXE.

The audit is deliberately narrow: it proves what can be proved from direct E8
calls to the standard fopen-like wrapper and from the executable's serialized
string pools.  It does not claim that indirect/custom file APIs do not exist.
"""
from pathlib import Path
import argparse, hashlib, json, struct

EXPECTED_EXE_SHA256 = "381e4f5c61e4bb8c27f06b1944e6673bbebc39ca219cc08fb9f948da2ca37c00"
LE_OFFSET = 0x37D4C
FOPEN_WRAPPER = 0x26004
LOW_LEVEL_OPEN = 0x3D006
EARLY_STRING_BASE = 0x11C558
LATE_STRING_BIAS = 0x2AA8
EXPECTED_FOPEN_CALLS = [
    0x0EF4,0x30D5,0x36C0,0x3790,0x499D,0x73BF,0x780E,0x8659,0x87F8,0x8ED4,
    0xB236,0xB2EE,0xBA1D,0xBF97,0xC885,0xCB61,0xD815,0xDAC5,0xDF54,0xED94,
    0x1000A,0x10201,0x10C7A,0x15188,0x15566,0x17849,0x17B31,0x195D3,0x19700,
    0x1EA33,0x1EA6A,0x1FB08,0x25467,0x27709,0x2950D,0x2A008,0x2A480,0x2A5A8,
    0x2A6B8,0x3610F,0x36271,0x362C7,0x36423,0x364B9,0x36649,0x371F7,0x4A4D7,
]
EXPECTED_LOW_LEVEL_CALLS = [0x25F98, 0x3CFFB]


def u32(buf, off):
    return struct.unpack_from('<I', buf, off)[0]


def build_objects(raw: bytes):
    if raw[LE_OFFSET:LE_OFFSET+2] != b'LE':
        raise SystemExit('validated LE header missing')
    le = raw[LE_OFFSET:]
    page_size = u32(le, 0x28)
    object_table = u32(le, 0x40)
    object_count = u32(le, 0x44)
    page_map = u32(le, 0x48)
    data_pages = u32(le, 0x80)
    objects = []
    for idx in range(object_count):
        size, base, flags, first_page, page_count, _ = struct.unpack_from('<IIIIII', le, object_table + 24*idx)
        page_span = bytearray(page_count * page_size)
        for logical_page in range(page_count):
            entoff = page_map + 4*(first_page - 1 + logical_page)
            ent = le[entoff:entoff+4]
            physical_page = (ent[0] << 16) | (ent[1] << 8) | ent[2]
            if not physical_page:
                continue
            src = LE_OFFSET + data_pages + (physical_page - 1)*page_size
            dst = logical_page * page_size
            n = min(page_size, max(0, len(raw)-src))
            if n:
                page_span[dst:dst+n] = raw[src:src+n]
        objects.append({
            'index': idx+1, 'virtual_size': size, 'base': base, 'flags': flags,
            'first_page': first_page, 'page_count': page_count,
            'page_span': bytes(page_span), 'virtual': bytes(page_span[:size]),
        })
    return objects


def calls_to(buf: bytes, target: int):
    out = []
    for i in range(len(buf)-5):
        if buf[i] != 0xE8:
            continue
        rel = int.from_bytes(buf[i+1:i+5], 'little', signed=True)
        if i + 5 + rel == target:
            out.append(i)
    return out


def cstr(buf: bytes, off: int, limit=512):
    if not (0 <= off < len(buf)):
        return None
    end = buf.find(b'\0', off, min(len(buf), off+limit))
    if end < 0:
        return None
    try:
        return buf[off:end].decode('latin1')
    except Exception:
        return None


def early_string(obj1_page_span: bytes, imm: int):
    return cstr(obj1_page_span, EARLY_STRING_BASE + imm)


def late_string(obj2_page_span: bytes, imm: int):
    return cstr(obj2_page_span, imm - LATE_STRING_BIAS)


def printable_c_strings(buf: bytes):
    out = []
    i = 0
    while i < len(buf):
        if 32 <= buf[i] < 127:
            j = i
            while j < len(buf) and 32 <= buf[j] < 127:
                j += 1
            if j < len(buf) and buf[j] == 0 and j-i >= 2:
                out.append((i, buf[i:j].decode('latin1')))
                i = j + 1
                continue
        i += 1
    return out


def imm32_occurrences(buf: bytes, value: int):
    needle = struct.pack('<I', value)
    out, pos = [], 0
    while True:
        pos = buf.find(needle, pos)
        if pos < 0:
            return out
        out.append(pos)
        pos += 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--exe', required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    raw = Path(args.exe).read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    objs = build_objects(raw)
    if len(objs) < 2:
        raise SystemExit('expected at least two LE objects')
    o1v, o1p = objs[0]['virtual'], objs[0]['page_span']
    o2p = objs[1]['page_span']

    fopen_calls = calls_to(o1v, FOPEN_WRAPPER)
    low_calls = calls_to(o1v, LOW_LEVEL_OPEN)

    early_anchors = {
        0x4CD: 'r', 0x4CF: 'MUSIC.DAT',
        0xE89: 'r', 0xE8B: 'characte.dat',
        0x13E3: 'r', 0x13E5: 'resource.cfg',
        0x184C: 'r', 0x184E: 'maps.dat',
        0x1909: 'r', 0x190B: 'MDI.INI',
        0x1A8C: 'r', 0x1A8E: 'CREDITS.TXT',
        0x284F: 'npc%d.dat', 0x2859: 'w',
        0x2904: 'npc%d.dat', 0x290E: 'r',
    }
    late_anchors = {
        0x2DC8: 'rb', 0x2DCB: 'hudmes.dat',
        0x2F50: 'r', 0x2F52: 'wirescan.res',
        0x3894: 'rb', 0x3897: 'objhud.dat',
        0x3B76: 'wb', 0x3B79: 'SGDNAME.DAT',
        0x3B98: 'wb', 0x3B9B: 'world.dat',
        0x3BA5: 'rb', 0x3BA8: 'world.dat',
        0x3BDD: 'AIL_SYS_DEBUG', 0x3BEB: 'w+t',
    }

    early_actual = {hex(k): early_string(o1p, k) for k in early_anchors}
    late_actual = {hex(k): late_string(o2p, k) for k in late_anchors}

    dat_strings = []
    for obj_index, buf in [(1, o1p), (2, o2p)]:
        for off, text in printable_c_strings(buf):
            if '.dat' in text.lower():
                dat_strings.append({'object': obj_index, 'offset': off, 'offset_hex': hex(off), 'text': text})

    expected_dat_texts = [
        'MUSIC.DAT', '%s.dat', 'characte.dat', 'con%d.dat', 'con%d.dat', 'maps.dat',
        'npc%d.dat', 'npc%d.dat', 'hudmes.dat', 'objhud.dat', 'SAVE%d.dat',
        'SGDNAME.DAT', 'SGDNAME.DAT', 'world.dat', 'world.dat',
    ]

    percent_s_dat_imm = 0xE3C
    percent_s_dat_xrefs = imm32_occurrences(o1v, percent_s_dat_imm)

    checks = {
        'exe_hash': sha == EXPECTED_EXE_SHA256,
        'object1_virtual_size': len(o1v) == 0x11E8DB,
        'object1_page_span': len(o1p) == 0x11F000,
        'object2_virtual_size': objs[1]['virtual_size'] == 0x57260,
        'direct_fopen_calls_exact_47': fopen_calls == EXPECTED_FOPEN_CALLS,
        'low_level_open_calls_exact_2': low_calls == EXPECTED_LOW_LEVEL_CALLS,
        'early_string_mapping': all(early_actual[hex(k)] == v for k,v in early_anchors.items()),
        'late_string_mapping': all(late_actual[hex(k)] == v for k,v in late_anchors.items()),
        'npc_strings_recovered_from_last_object1_page_tail': (
            early_string(o1p, 0x284F) == 'npc%d.dat' and early_string(o1p, 0x2904) == 'npc%d.dat'
            and EARLY_STRING_BASE + 0x284F >= objs[0]['virtual_size']
        ),
        'all_dat_strings_exact': [x['text'] for x in dat_strings] == expected_dat_texts,
        'literal_puzzles_dat_absent': b'puzzles.dat' not in o1p.lower() and b'puzzles.dat' not in o2p.lower(),
        'literal_puzzles_absent': b'puzzles' not in o1p.lower() and b'puzzles' not in o2p.lower(),
        'percent_s_dat_string': early_string(o1p, percent_s_dat_imm) == '%s.dat',
        'percent_s_dat_encoded_imm_unique': percent_s_dat_xrefs == [0x7389],
        'percent_s_dat_push_at_character_path': o1v[0x7388:0x738D] == bytes.fromhex('68 3c 0e 00 00'),
        'stdio_low_level_bridge': calls_to(o1v, LOW_LEVEL_OPEN)[0] == 0x25F98 and 0x25F98 > FOPEN_WRAPPER-0x100,
    }
    bad = [k for k,v in checks.items() if not v]
    if bad:
        raise SystemExit('v103 invariant failure: ' + ', '.join(bad))

    out = {
        'schema': 'openazrael.puzzles_fileio_census',
        'version': 103,
        'status': 'PASS',
        'exe_sha256': sha,
        'stdio': {
            'fopen_wrapper_object1_offset': FOPEN_WRAPPER,
            'fopen_wrapper_object1_offset_hex': hex(FOPEN_WRAPPER),
            'direct_game_and_runtime_calls': [hex(x) for x in fopen_calls],
            'direct_call_count': len(fopen_calls),
            'low_level_open_object1_offset': LOW_LEVEL_OPEN,
            'low_level_open_direct_calls': [hex(x) for x in low_calls],
            'note': 'Only the direct E8 call graph is asserted. Indirect calls and other/custom APIs remain outside this audit.',
        },
        'string_address_models': {
            'early_source_units': {
                'formula': 'object1 page-span offset = 0x11C558 + encoded immediate',
                'base': EARLY_STRING_BASE,
                'anchors': early_actual,
                'confidence': 'HIGH',
                'last_page_tail_note': 'npc%d.dat is referenced from bytes in the physical tail of object1 last page beyond the declared virtual byte size; the direct code/string relationship is VERIFIED for the bound image.',
            },
            'late_source_units': {
                'formula': 'object2 offset = encoded immediate - 0x2AA8',
                'bias': LATE_STRING_BIAS,
                'anchors': late_actual,
                'confidence': 'HIGH',
            },
        },
        'serialized_dat_strings': dat_strings,
        'percent_s_dat': {
            'encoded_immediate': percent_s_dat_imm,
            'encoded_immediate_hex': hex(percent_s_dat_imm),
            'occurrences_in_object1_virtual': [hex(x) for x in percent_s_dat_xrefs],
            'finding': 'The only static encoded reference to the generic %s.dat string is the already-closed v102 character path at 0x7388.',
            'confidence': 'VERIFIED',
        },
        'finding': {
            'direct_stdio_census': 'There are exactly 47 direct E8 calls to the standard fopen-like wrapper in object1 and exactly two direct calls to the lower open routine; one lower call is inside the stdio wrapper implementation.',
            'puzzles_literal': 'No PUZZLES.DAT/PUZZLES literal is present in the loaded/page-backed object string pools, and the sole generic %s.dat static reference is the character loader.',
            'implication': 'A simple literal-name or second static %s.dat PUZZLES loader route is excluded at HIGH confidence. This does not exclude dynamic/indirect/custom file access.',
            'puzzles_loader_identity': 'HOLD',
        },
        'checks': checks,
    }
    Path(args.out).write_text(json.dumps(out, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(f"PASS v103: fopen direct={len(fopen_calls)}, low-level direct={len(low_calls)}, DAT strings={len(dat_strings)}")

if __name__ == '__main__':
    main()
