#!/usr/bin/env python3
"""OpenAzrael v102: close the v101 ReadFlagData caller chain.

This is deliberately byte-level and bound to the known demo R.EXE.  It does
not attempt a general x86 disassembly.  The goal is to prove what the v101
ReadFlagData/%s.dat string cluster actually belongs to before using it as a
PUZZLES.DAT trace anchor.
"""
from pathlib import Path
import argparse, hashlib, json, struct

EXPECTED_EXE_SHA256 = "381e4f5c61e4bb8c27f06b1944e6673bbebc39ca219cc08fb9f948da2ca37c00"
LE_OFFSET = 0x37D4C
STRING_POOL_BASE = 0x11C558


def u32(buf, off):
    return struct.unpack_from('<I', buf, off)[0]


def build_obj1(raw: bytes) -> bytes:
    if raw[LE_OFFSET:LE_OFFSET+2] != b'LE':
        raise SystemExit('validated LE header missing')
    le = raw[LE_OFFSET:]
    page_size = u32(le, 0x28)
    object_table = u32(le, 0x40)
    page_map = u32(le, 0x48)
    data_pages = u32(le, 0x80)
    size, base, flags, first_page, page_count, _ = struct.unpack_from('<IIIIII', le, object_table)
    out = bytearray(size)
    for logical_page in range(page_count):
        ent = le[page_map + 4*(first_page-1+logical_page): page_map + 4*(first_page-1+logical_page)+4]
        physical_page = (ent[0] << 16) | (ent[1] << 8) | ent[2]
        if not physical_page:
            continue
        src = LE_OFFSET + data_pages + (physical_page-1)*page_size
        dst = logical_page*page_size
        n = min(page_size, size-dst, max(0, len(raw)-src))
        if n > 0:
            out[dst:dst+n] = raw[src:src+n]
    return bytes(out)


def cstr(buf: bytes, off: int, limit=256):
    if not (0 <= off < len(buf)):
        return None
    end = buf.find(b'\0', off, min(len(buf), off+limit))
    if end < 0:
        return None
    try:
        return buf[off:end].decode('latin1')
    except Exception:
        return None


def relstr(buf: bytes, imm: int):
    off = STRING_POOL_BASE + imm
    return {'imm': imm, 'imm_hex': hex(imm), 'object1_offset': off, 'object1_offset_hex': hex(off), 'text': cstr(buf, off)}


def calls_to(buf: bytes, target: int):
    """Raw E8 rel32 encodings targeting target. Evidence is strengthened by exact context checks below."""
    out = []
    for i in range(len(buf)-5):
        if buf[i] != 0xE8:
            continue
        rel = int.from_bytes(buf[i+1:i+5], 'little', signed=True)
        if i + 5 + rel == target:
            out.append(i)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--exe', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--demo-dir', required=True)
    args = ap.parse_args()

    raw = Path(args.exe).read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    obj = build_obj1(raw)
    demo_dir = Path(args.demo_dir)
    char_path = demo_dir / 'CHARACTE.DAT'
    niamh_path = demo_dir / 'NIAMH.DAT'
    char_bytes = char_path.read_bytes()
    niamh_bytes = niamh_path.read_bytes()

    # Exact source-unit string-offset model. The compiler code in this cluster
    # uses small immediates that map to object1 strings through one stable base.
    string_imms = [
        0xDA6, 0xDB7, 0xDBF, 0xDD0, 0xDD8, 0xDDB, 0xDE9, 0xDF4, 0xDFC,
        0xE01, 0xE06, 0xE0B, 0xE10, 0xE15, 0xE1A, 0xE2F, 0xE3C, 0xE43,
        0xE45, 0xE49, 0xE4D, 0xE51, 0xE55, 0xE59, 0xE5D, 0xE61, 0xE65,
        0xE89, 0xE8B, 0xE98, 0xE9B,
    ]
    strings = [relstr(obj, x) for x in string_imms]
    smap = {x['imm']: x['text'] for x in strings}

    expected_strings = {
        0xDA6: 'strlen too large', 0xDB7: 'GetLine', 0xDBF: 'strlen too large', 0xDD0: 'GetLine',
        0xDD8: '%d', 0xDDB: ',%d,%d,%d,%d\n', 0xDE9: ',%d,%d,%d\n', 0xDF4: ',%d,%d\n',
        0xDFC: ',%d\n', 0xE01: ',%d\n', 0xE06: ',%d\n', 0xE0B: ',%d\n', 0xE10: ',%d\n',
        0xE15: ',%d\n', 0xE1A: 'Invalid flag type %d', 0xE2F: 'ReadFlagData',
        0xE3C: '%s.dat', 0xE43: 'r', 0xE45: '%d\n', 0xE49: '%d\n', 0xE4D: '%d\n',
        0xE51: '%d\n', 0xE55: '%d\n', 0xE59: '%d\n', 0xE5D: '%d\n', 0xE61: '%d\n',
        0xE65: '%d\n', 0xE89: 'r', 0xE8B: 'characte.dat', 0xE98: '%d', 0xE9B: '%s',
    }

    checks = {
        'exe_hash': sha == EXPECTED_EXE_SHA256,
        'string_pool_model_all_expected': all(smap.get(k) == v for k, v in expected_strings.items()),
        # GetLine diagnostic pairs.
        'get_line_7164_diagnostics': obj[0x7186:0x7195] == bytes.fromhex('68a60d000068b70d0000e8139a0100'),
        'get_line_71ce_diagnostics': obj[0x71f0:0x71ff] == bytes.fromhex('68bf0d000068d00d0000e8a9990100'),
        # ReadFlagData: format-switch body and its own diagnostic/function-name pair.
        'readflagdata_entry': obj[0x7229:0x7238] == bytes.fromhex('515657c814000089c189d789de31db'),
        'readflagdata_type_scan': obj[0x7344:0x7368] == bytes.fromhex('8d45fc5068d80d000051e84a37020083c40c0fb7c38d04c08d14068a45fc88023c0877c3'),
        'readflagdata_invalid_type_diagnostic': obj[0x732b:0x7342] == bytes.fromhex('0fbe45fc50681a0e0000682f0e0000e86998010083c40c'),
        # Per-character <name>.dat reader: construct filename, open in r mode.
        'per_name_dat_entry': obj[0x7373:0x7388] == bytes.fromhex('515657c884000081ed8200000089c189556689da53'),
        'per_name_builds_percent_s_dat': obj[0x7388:0x7399] == bytes.fromhex('683c0e00008d45fe50e860f0010083c40c'),
        'per_name_opens_mode_r': obj[0x73b7:0x73c8] == bytes.fromhex('ba430e00008d45fee840ec010089c789c6'),
        'per_name_calls_getline': calls_to(obj, 0x7164) == [0x7456, 0x75BE, 0x7653, 0x76C1],
        'per_name_calls_readflagdata': calls_to(obj, 0x7229) == [0x7605, 0x764A, 0x7708],
        # Character list loader: literal characte.dat -> names -> per-name reader.
        'character_list_entry': obj[0x77F4:0x7804] == bytes.fromhex('5351525657c814000089c166c7000000'),
        'character_list_opens_characte_dat': obj[0x7804:0x7815] == bytes.fromhex('ba890e0000b88b0e0000e8f1e7010089c6'),
        'character_list_reads_count': obj[0x7819:0x782B] == bytes.fromhex('8d51025268980e000050e87532020083c40c'),
        'character_list_reads_name': obj[0x7845:0x7857] == bytes.fromhex('8d45ec50689b0e000056e84932020083c40c'),
        'character_list_calls_per_name_reader': obj[0x7857:0x7864] == bytes.fromhex('0fb7d78d5dec89c8e80ffbffff'),
        'single_raw_direct_call_to_per_name_reader': calls_to(obj, 0x7373) == [0x785F],
        'demo_characte_lists_one_niamh': char_bytes == b'1\r\nNiamh\r\n',
        'demo_niamh_dat_exists_and_is_text_flag_data': niamh_path.exists() and niamh_bytes.startswith(b'1\r\n1A\r\n1\r\n2\r\n3\r\n'),
    }

    bad = {k: v for k, v in checks.items() if not v}
    if bad:
        raise SystemExit('v102 invariant failed: ' + repr(bad))

    out = {
        'schema': 'openazrael.readflagdata_caller_chain',
        'version': 102,
        'status': 'PASS',
        'exe_sha256': sha,
        'string_pool': {
            'object1_base_offset': STRING_POOL_BASE,
            'object1_base_offset_hex': hex(STRING_POOL_BASE),
            'mapping': 'object1_string_offset = 0x11C558 + encoded_string_immediate',
            'entries': strings,
            'confidence': 'HIGH',
        },
        'routines': {
            '0x7164': {
                'role': 'GetLine-like helper',
                'evidence': ['uses strlen-too-large/GetLine diagnostic pair', 'called four times by 0x7373'],
                'confidence': 'HIGH',
            },
            '0x71CE': {
                'role': 'second GetLine-like helper',
                'evidence': ['uses second strlen-too-large/GetLine diagnostic pair', 'called from the same 0x7373 cluster'],
                'confidence': 'HIGH',
            },
            '0x7229': {
                'role': 'ReadFlagData parser',
                'evidence': [
                    'uses the exact ReadFlagData function-name string with Invalid flag type %d',
                    'reads a type byte/value then dispatches values 0..8 through a jump table',
                    'parses one-to-four comma-prefixed integer fields into compact flag records',
                    'all three direct E8 call encodings targeting it are inside 0x7373',
                ],
                'direct_call_sites': [hex(x) for x in calls_to(obj, 0x7229)],
                'confidence': 'HIGH',
            },
            '0x7373': {
                'role': 'per-character <name>.dat flag-data reader',
                'evidence': [
                    'formats a local filename with %s.dat',
                    'opens/loads that filename with mode r',
                    'uses GetLine-like helper(s) and ReadFlagData three times',
                    'its single raw direct E8 caller is in the characte.dat list loader at 0x785F',
                ],
                'direct_call_sites': [hex(x) for x in calls_to(obj, 0x7373)],
                'confidence': 'HIGH',
            },
            '0x77F4': {
                'role': 'CHARACTE.DAT list loader / dispatcher',
                'evidence': [
                    'opens literal characte.dat in mode r',
                    'reads a count with %d',
                    'iterates names with %s',
                    'passes each parsed name to 0x7373',
                ],
                'confidence': 'HIGH',
            },
        },
        'demo_file_crosscheck': {
            'CHARACTE.DAT': {
                'sha256': hashlib.sha256(char_bytes).hexdigest(),
                'bytes': len(char_bytes),
                'decoded_lines': char_bytes.decode('latin1').splitlines(),
            },
            'NIAMH.DAT': {
                'sha256': hashlib.sha256(niamh_bytes).hexdigest(),
                'bytes': len(niamh_bytes),
                'prefix_text': niamh_bytes[:96].decode('latin1', 'replace'),
            },
            'finding': 'The demo CHARACTE.DAT contains exactly one character name, Niamh, and NIAMH.DAT exists as the corresponding per-name text data file.',
            'confidence': 'VERIFIED',
        },
        'call_chain': [
            '0x77F4: open characte.dat -> read count -> read character name',
            '0x785F: call 0x7373 with that character name',
            '0x7373: build <name>.dat -> open/read file',
            '0x7373 -> 0x7164/0x71CE: GetLine-like helpers',
            '0x7373 -> 0x7229: ReadFlagData parser (three direct calls)',
        ],
        'invariants': checks,
        'correction': {
            'supersedes': 'v101 proposal to use ReadFlagData/%s.dat as a PUZZLES.DAT runtime trace anchor',
            'finding': 'The static caller chain binds this cluster to CHARACTE.DAT and per-character <name>.dat flag files. It is therefore not valid evidence for the PUZZLES.DAT loader.',
            'scope_caveat': 'The audit proves the observed direct caller chain. It does not claim that an indirect call to these helpers is impossible elsewhere; no such evidence is currently present.',
            'confidence': 'HIGH',
        },
        'puzzles_loader_status': {
            'ReadFlagData_as_puzzles_anchor': 'REJECTED/SUPERSEDED',
            'PUZZLES_DAT_loader': 'HOLD',
            'next': [
                'Do not breakpoint ReadFlagData as the primary PUZZLES loader probe.',
                'Audit other file-open/read call families and non-literal filename construction paths.',
                'Use the now-decoded source-unit string-offset model where applicable, but derive each compilation-unit string base independently rather than assuming one global base.',
            ],
        },
    }

    Path(args.out).write_text(json.dumps(out, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps({
        'status': 'PASS',
        'string_pool_entries': len(strings),
        'readflagdata_direct_call_sites': [hex(x) for x in calls_to(obj, 0x7229)],
        'per_name_reader_direct_call_sites': [hex(x) for x in calls_to(obj, 0x7373)],
        'correction': 'ReadFlagData path -> CHARACTE/per-character flag data, not PUZZLES loader evidence',
        'checks': len(checks),
    }, indent=2))


if __name__ == '__main__':
    main()
