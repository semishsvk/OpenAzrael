#!/usr/bin/env python3
"""Extract a pinned startup contract from corrected original R.EXE coordinates.

This records original call arguments/control flow, not measured DOS wall time.
Source movie frame periods are caller parameters; MOV header value 12 is opaque.
"""
from __future__ import annotations
import hashlib, json, struct
from pathlib import Path
from le_bound_image_v312 import BoundLE, need, u32

EXE_SHA = '381e4f5c61e4bb8c27f06b1944e6673bbebc39ca219cc08fb9f948da2ca37c00'
TITLE_SHA = 'd0fb123f1cad349cdabfd8e3dce2950be4a6fdcd54316d3bb62e04ea751222a2'
RESOURCE_CFG_SHA = '1ec1259f01739853b2516a9449659e10fa916c9ca516bd70e4079c517bc31d04'

def extract(corpus: Path) -> dict:
    raw = (corpus / 'R.EXE').read_bytes()
    need(hashlib.sha256(raw).hexdigest() == EXE_SHA, 'unbound original executable')
    image = BoundLE.parse(raw)
    code = image.objects[0].data
    need(image.report()['raw_operand_target_matches'] == 28547, 'relocation/operand mismatch')
    def constant(address: int, opcode: int):
        need(code[address] == opcode, 'unexpected source instruction')
        return u32(code, address + 1)
    sites = {'MINDLOGO': (0x107a2, 0x107ac), 'INTRO': (0x107fb, 0x10805),
             'MOV_INTRO': (0x108c7, 0x108cf), 'MOV_DEMO': (0x10970, 0x10978)}
    clips = {}
    for clip_id, (argument, call) in sites.items():
        fps = constant(argument, 0xba)
        need(code[call] == 0xe8 and call + 5 + struct.unpack_from('<i', code, call + 1)[0] == 0x112d0,
             'movie call target mismatch')
        period = 1_000_000 // fps
        clips[clip_id] = {'nominal_fps': fps, 'frame_period_us': period,
                          'fps': 1_000_000 / period, 'argument_instruction': argument, 'call_instruction': call}
    need(constant(0x112fe, 0xb8) == 1_000_000 and code[0x1130f:0x11311] == b'\xf7\xfb', 'timer division mismatch')
    need(constant(0x113b4, 0xb8) == 480 and constant(0x113d3, 0xb8) == 640, 'logical display geometry mismatch')
    hold_step = constant(0x1085e, 0xb8)
    need(code[0x10869:0x1086b] == b'\x81\xfa', 'title loop bound instruction mismatch')
    hold_count = u32(code, 0x1086b)
    need((hold_step, hold_count) == (20, 130), 'unexpected title loop')
    need(constant(0x10fec, 0xbb) == 22050, 'PCM rate argument mismatch')
    title = (corpus / 'TITLE.PCX').read_bytes()
    need(hashlib.sha256(title).hexdigest() == TITLE_SHA, 'unbound title source')
    xmin, ymin, xmax, ymax = struct.unpack_from('<4H', title, 4)
    need((xmin, ymin, xmax, ymax) == (0, 0, 630, 473), 'unexpected title dimensions')
    config = (corpus / 'RESOURCE.CFG').read_bytes()
    need(hashlib.sha256(config).hexdigest() == RESOURCE_CFG_SHA, 'unbound resource configuration')
    movie_prefix = config.splitlines()[2].decode('ascii')
    need(movie_prefix.lower() == 'mov\\', 'unexpected movie directory')
    need(code[0xba89:0xba8f] == bytes.fromhex('890d10230200'), 'resource-prefix assignment changed')
    return {
        'schema': 'openazrael.intro_source_contract.v312',
        'resource_cfg_sha256': RESOURCE_CFG_SHA, 'movie_directory': movie_prefix,
        'movie_directory_initializer': 0xb962, 'movie_directory_assignment': 0xba89, 'exe_sha256': EXE_SHA,
        'coordinate_space': 'corrected_LE_object1_relative', 'module_file_offset': image.module_file_offset,
        'header_file_offset': image.header_file_offset, 'data_file_offset': image.data_file_offset,
        'startup_order': ['MINDLOGO', 'INTRO', 'TITLE', 'MOV_INTRO'],
        'startup_function': 0x10799, 'startup_caller': 0x5f3c, 'clips': clips,
        'logical_canvas': [640, 480], 'movie_placement': 'integer_center_in_640x480',
        'title': {'source': 'TITLE.PCX', 'source_sha256': TITLE_SHA, 'width': 631, 'height': 474,
                  'origin': [0, 0], 'placement_authority': 'original PCX decoder at 0x2ca90 into 640x480 buffer with caller x=y=0',
                  'wait_argument': hold_step, 'wait_count': hold_count,
                  'nominal_hold_seconds': hold_step * hold_count / 1000,
                  'timing_scope': 'source delay arguments; actual DOS calibration/fade timing HOLD'},
        'pcm_sample_rate': 22050,
        'demo_outro': {'clip': 'MOV_DEMO', 'function': 0x10919, 'caller': 0x607a, 'startup': False},
        'not_verified': ['DOS/VGA wall-clock capture', 'palette fade curves', 'DAC-to-display conversion',
                         'physical audio latency', 'original input-key mapping', 'full KG-001 fidelity'],
    }

if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description=__doc__); ap.add_argument('corpus', type=Path); ap.add_argument('--out', type=Path)
    a = ap.parse_args(); result = extract(a.corpus)
    text = json.dumps(result, indent=2) + '\n'
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True); a.out.write_text(text, encoding='utf8')
    print(text)
