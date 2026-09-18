#!/usr/bin/env python3
"""OpenAzrael v104: classify every direct call to the bound R.EXE fopen wrapper.

This advances v103 from a census to a source/subsystem classification.  The
result is intentionally limited to direct E8 calls; indirect/custom I/O stays
out of scope and is the next loader-hunting frontier.
"""
from pathlib import Path
import argparse, hashlib, json, struct, sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_file_open_families_v103 import (
    EXPECTED_EXE_SHA256, build_objects, calls_to, early_string, late_string,
    FOPEN_WRAPPER, EXPECTED_FOPEN_CALLS,
)

# site, family, evidence immediate, expected string, mapping, path/mode note, confidence
CATALOG = [
(0x0EF4,'music_table','literal','MUSIC.DAT',0x4CF,'early','read text table','VERIFIED'),
(0x30D5,'book_text','formatted','books\\%s.bok',0x691,'early','read generated book path','HIGH'),
(0x36C0,'book_text','formatted','books\\%s.bok',0x691,'early','read generated book path','HIGH'),
(0x3790,'book_pcx','formatted','%s\\books\\%s%d.pcx',0x72F,'early','read binary PCX path','HIGH'),
(0x499D,'wire_scan_pcx','formatted','%swire\\%s%02d.pcx',0x9CE,'early','read binary wire/scan PCX','HIGH'),
(0x73BF,'character_flag_data','formatted','%s.dat',0xE3C,'early','v102 per-character text flags','VERIFIED'),
(0x780E,'character_list','literal','characte.dat',0xE8B,'early','read character list','VERIFIED'),
(0x8659,'conversation_data','formatted','con%d.dat',0x1045,'early','write conversation state/data','HIGH'),
(0x87F8,'conversation_data','formatted','con%d.dat',0x1068,'early','read conversation state/data','HIGH'),
(0x8ED4,'resource_config','literal','resource.cfg',0x13E5,'early','read resource configuration','VERIFIED'),
(0xB236,'room_animation','formatted','RANIM%d.ANM',0x1784,'early','read room animation','HIGH'),
(0xB2EE,'room_animation','formatted','RANIM%d.ANM',0x1784,'early','write room animation','HIGH'),
(0xBA1D,'gif_image','diagnostic','Loadgif could not find file %s\n',0x17B0,'early','GIF loader','HIGH'),
(0xBF97,'azf_texture','diagnostic','LoadAZF could not find file %s\n',0x1810,'early','AZF loader','HIGH'),
(0xC885,'map_table','literal','maps.dat',0x184E,'early','read map table','VERIFIED'),
(0xCB61,'midi_config','literal','MDI.INI',0x190B,'early','read MIDI configuration','VERIFIED'),
(0xD815,'ambient_snd','formatted','AMB%d.SND',0x1A2A,'early','read ambient placement file','VERIFIED'),
(0xDAC5,'credits_text','literal','CREDITS.TXT',0x1A8E,'early','read credits','VERIFIED'),
(0xDF54,'animation_binary','diagnostic','IAnimation',0x1B3C,'early','binary animation loader','HIGH'),
(0xED94,'character_animation','diagnostic','ICharacterAnim',0x1C69,'early','character ANI text loader','HIGH'),
(0x1000A,'dead_character_save','formatted','DEDCHA%d.SAV',0x1FDE,'early','read dead-character save','HIGH'),
(0x10201,'dead_character_save','formatted','DEDCHA%d.SAV',0x20EE,'early','write dead-character save','HIGH'),
(0x10C7A,'character_animation','diagnostic','ICharacterAnim',0x1C69,'early','second character ANI loader path','HIGH'),
(0x15188,'npc_state_text','formatted','npc%d.dat',0x284F,'early','NPC text writer; fprintf-like path','VERIFIED'),
(0x15566,'npc_state_text','formatted','npc%d.dat',0x2904,'early','NPC text reader; fscanf-like path','VERIFIED'),
(0x17849,'xaf_scene','diagnostic','XAFLoadAsList',0x2DBA,'late','XAF text scene loader','HIGH'),
(0x17B31,'hud_messages','literal','hudmes.dat',0x2DCB,'late','read HUD message table','VERIFIED'),
(0x195D3,'wire_scan_resource','literal','wirescan.res',0x2F52,'late','read wire-scan resource','VERIFIED'),
(0x19700,'object_description','formatted','%s.DES',0x2F6C,'late','read object description text','HIGH'),
(0x1EA33,'sample_audio','diagnostic','Cannot open sample file %s\n',0x3297,'late','Miles/sample loader','HIGH'),
(0x1EA6A,'sample_audio','diagnostic','Cannot open sample file %s\n',0x3297,'late','Miles/sample loader','HIGH'),
(0x1FB08,'sample_audio','diagnostic','PlayDoubleBuffer',0x32FC,'late','double-buffer sample loader','HIGH'),
(0x25467,'font_pcx','diagnostic','LoadFont',0x3764,'late','font PCX loader','HIGH'),
(0x27709,'music_stream','diagnostic','DoLoadMusic',0x3887,'late','music loader','HIGH'),
(0x2950D,'object_hud','literal','objhud.dat',0x3897,'late','read object HUD table','VERIFIED'),
(0x2A008,'pcx_image','diagnostic','LoadPCX',0x38C4,'late','PCX loader source unit','HIGH'),
(0x2A480,'pcx_palette','diagnostic','LoadPCXPal',0x390C,'late','PCX palette loader','HIGH'),
(0x2A5A8,'pcx_palette','diagnostic','LoadPCXPal',0x390C,'late','PCX palette loader','HIGH'),
(0x2A6B8,'pcx_writer','mode','wb',0x39B0,'late','PCX-like writer; emits 0A/05/01/08 header fields','HIGH'),
(0x3610F,'save_game_slot','formatted','SAVE%d.dat',0x3B68,'late','write save slot','VERIFIED'),
(0x36271,'save_game_index','literal','SGDNAME.DAT',0x3B79,'late','write save-name index','VERIFIED'),
(0x362C7,'save_game_slot','formatted','SAVE%d.dat',0x3B68,'late','read save slot','VERIFIED'),
(0x36423,'save_game_index','literal','SGDNAME.DAT',0x3B8B,'late','read save-name index','VERIFIED'),
(0x364B9,'world_save','literal','world.dat',0x3B9B,'late','write world state','VERIFIED'),
(0x36649,'world_save','literal','world.dat',0x3BA8,'late','read world state','VERIFIED'),
(0x371F7,'miles_debug_log','diagnostic','AIL_SYS_DEBUG',0x3BDD,'late','Miles diagnostic trace output','HIGH'),
(0x4A4D7,'miles_driver_config','diagnostic','DRIVER',0x4E60,'late','Miles driver/config text parser','HIGH'),
]


def call_target(buf, site):
    if buf[site] != 0xE8:
        return None
    rel = int.from_bytes(buf[site+1:site+5], 'little', signed=True)
    return site + 5 + rel


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--exe',required=True)
    ap.add_argument('--out',required=True)
    args=ap.parse_args()
    raw=Path(args.exe).read_bytes()
    sha=hashlib.sha256(raw).hexdigest()
    objs=build_objects(raw)
    o1v,o1p=objs[0]['virtual'],objs[0]['page_span']
    o2p=objs[1]['page_span']
    direct=calls_to(o1v,FOPEN_WRAPPER)

    rows=[]
    evidence_fail=[]
    for site,family,kind,text,imm,mapping,note,confidence in CATALOG:
        resolved=early_string(o1p,imm) if mapping=='early' else late_string(o2p,imm)
        window=o1v[max(0,site-0x900):min(len(o1v),site+0x900)]
        imm_seen=struct.pack('<I',imm) in window
        target=call_target(o1v,site)
        ok=(resolved==text and imm_seen and target==FOPEN_WRAPPER)
        if not ok:
            evidence_fail.append({'site':hex(site),'resolved':resolved,'expected':text,'imm_seen':imm_seen,'target':target})
        rows.append({
            'site':site,'site_hex':hex(site),'family':family,'evidence_kind':kind,
            'evidence_string':text,'encoded_string_immediate':imm,'encoded_string_immediate_hex':hex(imm),
            'mapping':mapping,'note':note,'confidence':confidence,'evidence_check':ok,
        })

    # Strong behavioral checks for the two formerly unresolved mid-file NPC calls.
    npc_writer_fprintf = call_target(o1v,0x1519D) == 0x2B74C
    npc_reader_fscanf = call_target(o1v,0x15580) == 0x2AA9D
    pcx_header_signature = (
        o1v[0x2A6B1:0x2A6BD] == bytes.fromhex('ba b0 39 00 00 b3 01 e8 47 b9 ff ff')
        and b'\xb2\x0a' in o1v[0x2A6B8:0x2A720]
        and b'\xb7\x08' in o1v[0x2A6B8:0x2A720]
        and b'\xb6\x05' in o1v[0x2A6B8:0x2A720]
    )
    driver_tokens = all((s.encode('ascii') in o2p) for s in ['DRIVER','DEVICE','IO_ADDR','IRQ','DMA_8_bit','DMA_16_bit'])

    catalog_sites=[x[0] for x in CATALOG]
    checks={
        'exe_hash':sha==EXPECTED_EXE_SHA256,
        'direct_call_set_unchanged_from_v103':direct==EXPECTED_FOPEN_CALLS,
        'catalog_has_exactly_47_rows':len(CATALOG)==47,
        'catalog_covers_every_direct_call_once':catalog_sites==EXPECTED_FOPEN_CALLS and len(set(catalog_sites))==47,
        'all_string_evidence_resolves_and_is_code_local':not evidence_fail,
        'npc_writer_uses_fprintf_like_helper':npc_writer_fprintf,
        'npc_reader_uses_fscanf_like_helper':npc_reader_fscanf,
        'pcx_writer_header_signature':pcx_header_signature,
        'miles_driver_parser_tokens_present':driver_tokens,
        'no_catalog_family_claims_puzzles':all('puzzle' not in r['family'].lower() and 'puzzle' not in r['note'].lower() for r in rows),
    }
    bad=[k for k,v in checks.items() if not v]
    if bad:
        raise SystemExit('v104 invariant failure: '+', '.join(bad)+' details='+repr(evidence_fail[:4]))

    counts={}
    for r in rows:
        counts[r['family']]=counts.get(r['family'],0)+1
    out={
        'schema':'openazrael.direct_fopen_classification',
        'version':104,'status':'PASS','exe_sha256':sha,
        'direct_fopen_wrapper_offset':FOPEN_WRAPPER,
        'direct_call_count':len(direct),
        'classified_call_count':len(rows),
        'family_counts':dict(sorted(counts.items())),
        'calls':rows,
        'behavioral_crosschecks':{
            'npc_writer_0x15188':'Exact npc%d.dat path; subsequent call at 0x1519D targets fprintf-like 0x2B74C.',
            'npc_reader_0x15566':'Exact npc%d.dat path; subsequent call at 0x15580 targets fscanf-like 0x2AA9D.',
            'pcx_writer_0x2A6B8':'wb open followed by canonical PCX header bytes 0x0A, version 5, encoding 1, 8 bpp in the constructed header.',
            'driver_config_0x4A4D7':'rt open in source cluster containing DRIVER/DEVICE/IO_ADDR/IRQ/DMA tokens.',
        },
        'finding':{
            'direct_stdio_result':'All 47 direct E8 calls to the standard fopen-like wrapper are accounted for by non-PUZZLES resource, character/NPC, image, audio, configuration, or save/load subsystems.',
            'confidence':'HIGH',
            'important_limit':'This excludes only direct calls to 0x26004. It does not exclude indirect calls, a different/custom file API, a resource-container abstraction, or the possibility that PUZZLES.DAT is transformed by another path.',
            'puzzles_loader_identity':'HOLD',
            'next_step':'Audit indirect calls and alternative read/open APIs, then correlate candidate readers with the 190-byte/FE+128 PUZZLES record grammar.',
        },
        'checks':checks,
    }
    Path(args.out).write_text(json.dumps(out,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print('PASS v104: 47/47 direct fopen calls classified; PUZZLES direct-fopen candidate count=0')

if __name__=='__main__':
    main()
