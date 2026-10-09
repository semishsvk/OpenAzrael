#!/usr/bin/env python3
"""OpenAzrael v105: audit direct non-fopen file-open routes in bound demo R.EXE.

v103/v104 closed all direct calls to the stdio fopen wrapper.  This audit
covers the next two obvious bypasses:
  1) direct calls to the C runtime low-level `_open`-style wrapper; and
  2) direct DOS INT 21h file-open service (AH=3Dh) sites.

The audit is intentionally static and direct-call/direct-instruction only.
Indirect function pointers, custom resource abstractions, and authoring-time
compilation remain outside its proof boundary.
"""
from pathlib import Path
import argparse, hashlib, json, struct, sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_file_open_families_v103 import (
    EXPECTED_EXE_SHA256, build_objects, calls_to, late_string,
    FOPEN_WRAPPER, LOW_LEVEL_OPEN,
)

RAW_OPEN_WRAPPER = 0x3CFE2
EXPECTED_RAW_OPEN_CALLS = [0x49191, 0x492C2, 0x49729, 0x497BA, 0x49817, 0x49877]
EXPECTED_LOW_LEVEL_CALLS = [0x25F98, 0x3CFFB]
EXPECTED_DOS_OPEN_INT21 = [0x2B6D2, 0x3D038, 0x3D13C]


def call_target(buf: bytes, site: int):
    if site < 0 or site + 5 > len(buf) or buf[site] != 0xE8:
        return None
    rel = int.from_bytes(buf[site+1:site+5], 'little', signed=True)
    return site + 5 + rel


def all_int21(buf: bytes):
    out=[]; p=0
    while True:
        p=buf.find(b'\xCD\x21',p)
        if p < 0:
            return out
        out.append(p)
        p += 2


def dos_open_sites(buf: bytes):
    """Conservative direct AH=3Dh/AX=3Dxx scan immediately before INT 21h.

    We recognize only explicit instruction encodings close enough that the
    service number is unambiguous:
      B4 3D CD 21                 mov ah,3Dh ; int 21h
      66 B8 xx 3D CD 21           mov ax,3Dxxh ; int 21h (operand-size 16)
      B8 xx 3D 00 00 CD 21        mov eax,00003Dxxh ; int 21h
    This intentionally does not infer register values across arbitrary code.
    """
    out=[]
    for p in all_int21(buf):
        if p >= 2 and buf[p-2:p] == b'\xB4\x3D':
            out.append(p)
            continue
        if p >= 4 and buf[p-4] == 0x66 and buf[p-3] == 0xB8 and buf[p-1] == 0x3D:
            out.append(p)
            continue
        if p >= 5 and buf[p-5] == 0xB8 and buf[p-3:p] == b'\x3D\x00\x00':
            out.append(p)
            continue
    return out


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--exe',required=True)
    ap.add_argument('--out',required=True)
    args=ap.parse_args()

    raw=Path(args.exe).read_bytes()
    sha=hashlib.sha256(raw).hexdigest()
    objs=build_objects(raw)
    o1=objs[0]['virtual']
    o2=objs[1]['page_span']

    raw_open_calls=calls_to(o1,RAW_OPEN_WRAPPER)
    low_calls=calls_to(o1,LOW_LEVEL_OPEN)
    dos_sites=dos_open_sites(o1)

    # The six direct _open-wrapper calls are all in the Miles/Ail support
    # block.  The surrounding source families independently expose DIG.INI,
    # MDI.INI and driver diagnostics through the already validated late-string
    # address model.
    late_anchors={
        0x4E48:'LX',
        0x5050:'Driver file not found\n',
        0x5068:'DIG.INI',
        0x5070:'Unable to open file DIG.INI\n',
        0x5250:'Driver file not found\n',
        0x5268:'MDI.INI',
        0x5270:'Unable to open file MDI.INI\n',
    }
    late_actual={hex(k):late_string(o2,k) for k in late_anchors}

    # Shared AIL file helpers are reached from both the DIG and MDI source
    # clusters.  These direct call edges are concrete and deterministic.
    bridge_edges={
        'dig_file_read_to_0x49763': call_target(o1,0x4C091),
        'dig_file_size_to_0x49717': call_target(o1,0x4C0B7),
        'mdi_file_read_to_0x49763': call_target(o1,0x4EF21),
        'mdi_file_size_to_0x49717': call_target(o1,0x4EF47),
        'generic_read_calls_size_helper': call_target(o1,0x49772),
    }

    rows=[
        {'site':0x49191,'role':'AIL shared driver-image open','classification':'MILES_DRIVER_IO','confidence':'HIGH'},
        {'site':0x492C2,'role':'AIL shared driver-image open, second loader path','classification':'MILES_DRIVER_IO','confidence':'HIGH'},
        {'site':0x49729,'role':'AIL generic file-size/helper open','classification':'MILES_FILE_HELPER','confidence':'HIGH'},
        {'site':0x497BA,'role':'AIL generic file-read helper second open','classification':'MILES_FILE_HELPER','confidence':'HIGH'},
        {'site':0x49817,'role':'AIL generic file copy/write helper open','classification':'MILES_FILE_HELPER','confidence':'HIGH'},
        {'site':0x49877,'role':'AIL generic file copy/write helper open, alternate mode','classification':'MILES_FILE_HELPER','confidence':'HIGH'},
    ]
    for r in rows:
        r['site_hex']=hex(r['site'])
        r['target']=call_target(o1,r['site'])
        r['target_hex']=hex(r['target']) if r['target'] is not None else None

    # Direct DOS file-open instructions.  0x3D038 and 0x3D13C are inside the
    # same low-level open implementation.  0x2B6D2 explicitly requests AX=
    # 3D01h (write-only open), writes with AH=40h, then terminates via AH=4Ch;
    # it cannot be a PUZZLES read path.
    dos_rows=[
        {
            'int21_site':0x2B6D2,'int21_site_hex':hex(0x2B6D2),
            'service':'AX=3D01h (open existing write-only)',
            'classification':'CRT_FATAL_EXIT_WRITE_PATH','confidence':'HIGH',
            'evidence':'Within the same short path, AH=40h writes to the handle and AH=4Ch terminates the process; no read service occurs.',
        },
        {
            'int21_site':0x3D038,'int21_site_hex':hex(0x3D038),
            'service':'AH=3Dh','classification':'LOW_LEVEL_OPEN_IMPLEMENTATION','confidence':'VERIFIED',
            'evidence':'Primary DOS open inside object1+0x3D006 low-level open routine.',
        },
        {
            'int21_site':0x3D13C,'int21_site_hex':hex(0x3D13C),
            'service':'AH=3Dh','classification':'LOW_LEVEL_OPEN_IMPLEMENTATION','confidence':'VERIFIED',
            'evidence':'Fallback/reopen branch inside the same object1+0x3D006 low-level open routine.',
        },
    ]

    checks={
        'exe_hash': sha==EXPECTED_EXE_SHA256,
        'raw_open_wrapper_calls_exact_6': raw_open_calls==EXPECTED_RAW_OPEN_CALLS,
        'raw_open_wrapper_calls_low_level_open': call_target(o1,0x3CFFB)==LOW_LEVEL_OPEN,
        'low_level_open_direct_call_set': low_calls==EXPECTED_LOW_LEVEL_CALLS,
        'stdio_bridge_is_one_low_level_caller': call_target(o1,0x25F98)==LOW_LEVEL_OPEN,
        'all_raw_open_sites_target_wrapper': all(r['target']==RAW_OPEN_WRAPPER for r in rows),
        'late_miles_strings_resolve': all(late_actual[hex(k)]==v for k,v in late_anchors.items()),
        'dig_bridge_calls_generic_helpers': bridge_edges['dig_file_read_to_0x49763']==0x49763 and bridge_edges['dig_file_size_to_0x49717']==0x49717,
        'mdi_bridge_calls_generic_helpers': bridge_edges['mdi_file_read_to_0x49763']==0x49763 and bridge_edges['mdi_file_size_to_0x49717']==0x49717,
        'generic_read_calls_size_helper': bridge_edges['generic_read_calls_size_helper']==0x49717,
        'direct_dos_open_sites_exact_3': dos_sites==EXPECTED_DOS_OPEN_INT21,
        'fatal_path_is_write_only_open': o1[0x2B6CE:0x2B6D2]==bytes.fromhex('66 b8 01 3d'),
        'fatal_path_has_dos_write': b'\xB4\x40\xCD\x21' in o1[0x2B6D2:0x2B700],
        'fatal_path_has_process_exit': b'\xB4\x4C\xCD\x21' in o1[0x2B6D2:0x2B710],
        'no_direct_alt_open_row_claims_puzzles': all('PUZZLE' not in r['classification'] for r in rows),
    }
    bad=[k for k,v in checks.items() if not v]
    if bad:
        raise SystemExit('v105 invariant failure: '+', '.join(bad)+f' raw={list(map(hex,raw_open_calls))} dos={list(map(hex,dos_sites))} late={late_actual} edges={bridge_edges}')

    out={
        'schema':'openazrael.alternative_open_paths',
        'version':105,'status':'PASS','exe_sha256':sha,
        'known_standard_stdio':{
            'fopen_wrapper':FOPEN_WRAPPER,'fopen_wrapper_hex':hex(FOPEN_WRAPPER),
            'note':'v104 already classified all 47 direct calls to this wrapper as non-PUZZLES.',
        },
        'low_level_open':{
            'implementation':LOW_LEVEL_OPEN,'implementation_hex':hex(LOW_LEVEL_OPEN),
            'direct_callers':[{'site':x,'site_hex':hex(x)} for x in low_calls],
            'wrapper':RAW_OPEN_WRAPPER,'wrapper_hex':hex(RAW_OPEN_WRAPPER),
            'wrapper_direct_calls':rows,
            'miles_late_string_anchors':late_actual,
            'miles_bridge_edges':{k:(hex(v) if v is not None else None) for k,v in bridge_edges.items()},
        },
        'dos_int21_open':{
            'recognized_direct_open_sites':[hex(x) for x in dos_sites],
            'sites':dos_rows,
            'scanner_scope':'Only explicit AH=3Dh/AX=3Dxx assignments immediately adjacent to INT 21h are recognized; arbitrary dataflow into AH is not inferred.',
        },
        'finding':{
            'result':'The direct non-fopen routes are also accounted for: all six direct calls to the C runtime _open-style wrapper belong to the Miles/Ail driver/file-helper block, and the only direct DOS AH=3Dh site outside that low-level implementation is a write-only fatal/exit path.',
            'confidence':'HIGH',
            'puzzles_direct_read_candidate_count':0,
            'important_limit':'This still does not exclude an indirect function-pointer call, a custom/resource API that does not use the recognized open routes, preloaded/container data, or the possibility that PUZZLES.DAT is authoring input rather than a runtime-read file.',
            'puzzles_loader_identity':'HOLD',
            'next_step':'Test the authoring/compiled-data hypothesis by correlating PUZZLES.DAT/ROOMS.DAT with the runtime-opened WORLD.DAT and by tracing WORLD.DAT loader behavior rather than assuming PUZZLES.DAT is opened at runtime.',
        },
        'checks':checks,
    }
    Path(args.out).write_text(json.dumps(out,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print('PASS v105: alternative direct open routes classified; direct PUZZLES read candidates=0')

if __name__=='__main__':
    main()
