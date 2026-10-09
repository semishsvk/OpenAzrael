#!/usr/bin/env python3
"""Execute SHA-pinned R.EXE i386 mechanisms in an isolated Unicorn fixture.

This is original-executable mechanism equivalence, NOT a DOS/VGA hardware run.
Huffman, keyframe and delta instructions execute unmodified after real LE
relocations. Startup I/O/display/delay callees are explicit stubs; control flow
and arguments execute in the original caller. No replacement video decoder is
used as the native oracle. CPU time/instruction bounds fail closed.
"""
from __future__ import annotations
import argparse, collections, hashlib, json, struct, sys, time
from pathlib import Path
from le_bound_image_v312 import BoundLE, need
import decode_intro_mov_v311 as reconstructed

EXE_SHA = '381e4f5c61e4bb8c27f06b1944e6673bbebc39ca219cc08fb9f948da2ca37c00'
CODE, DATA = 0x10000, 0x130000
CTX, D1, D2, SRC, DST, PREV = 0x300000, 0x300100, 0x300200, 0x400000, 0x500000, 0x600000
STOP, STACK = 0x800000, 0x8ff000

def sha(b):
    return hashlib.sha256(b).hexdigest()

class Native:
    def __init__(self, image):
        import unicorn
        from unicorn import x86_const
        self.uc, self.regs = unicorn, x86_const
        self.mu = unicorn.Uc(unicorn.UC_ARCH_X86, unicorn.UC_MODE_32)
        self.mu.mem_map(CODE, 0x190000)
        for obj, payload in zip(image.objects, image.relocated_objects()):
            self.mu.mem_write(obj.base, payload)
        self.mu.mem_map(0x200000, 0x1000)
        self.mu.mem_write(0x200000, struct.pack('<QQQ', 0, 0x00cf9a000000ffff, 0x00cf92000000ffff))
        self.set('GDTR', (0, 0x200000, 23, 0)); self.set('CS', 8)
        for name in ('DS', 'ES', 'SS', 'FS', 'GS'):
            self.set(name, 16)
        self.mu.mem_map(0x300000, 0x400000)
        self.mu.mem_map(0x800000, 0x100000)
        self.version = unicorn.__version__
        self.calls = 0

    def get(self, name):
        return self.mu.reg_read(getattr(self.regs, 'UC_X86_REG_' + name))

    def set(self, name, value):
        self.mu.reg_write(getattr(self.regs, 'UC_X86_REG_' + name), value)

    def write32(self, address, value):
        self.mu.mem_write(address, struct.pack('<I', value))

    def read32(self, address):
        return struct.unpack('<I', self.mu.mem_read(address, 4))[0]

    def cstr(self, address):
        raw = bytes(self.mu.mem_read(address, 256))
        need(b'\0' in raw, 'unterminated oracle string')
        return raw.split(b'\0')[0].decode('ascii')

    def return_stub(self, stack_bytes=0):
        sp = self.get('ESP'); dest = self.read32(sp)
        self.set('ESP', sp + 4 + stack_bytes); self.set('EIP', dest)

    def call(self, entry, eax=0, edx=0, ebx=0, args=(), permitted_stop=STOP, ecx=0):
        for reg in ('EAX', 'EBX', 'ECX', 'EDX', 'ESI', 'EDI', 'EBP'):
            self.set(reg, 0)
        self.set('ESP', STACK); self.set('EFLAGS', 2)
        self.set('EAX', eax); self.set('EDX', edx); self.set('EBX', ebx); self.set('ECX', ecx)
        self.mu.mem_write(STACK, struct.pack('<' + 'I' * (1 + len(args)), STOP, *args))
        self.calls += 1
        self.mu.emu_start(CODE + entry, STOP, timeout=5000000, count=100000000)
        need(self.get('EIP') == permitted_stop, 'native execution exceeded bound or stopped unexpectedly')

    def setup_frame(self, width, height):
        self.mu.mem_write(CTX, b'\0' * 256)
        self.mu.mem_write(CTX + 10, struct.pack('<IIHH', D1, D2, width, height))
        self.mu.mem_write(D1, struct.pack('<HHI', width, height, DST))
        self.mu.mem_write(D2, struct.pack('<HHI', width, height, PREV))
        self.mu.mem_write(DST, b'\0' * (width * height))
        self.mu.mem_write(PREV, b'\0' * (width * height))

    def timer_period(self, fps):
        values = []
        def hook(uc, address, size, user):
            off = address - CODE
            if off in (0x20a90, 0x109a0):
                self.return_stub()
            elif off == 0x20abc:
                values.append(self.get('EDX')); uc.emu_stop()
        handle = self.mu.hook_add(self.uc.UC_HOOK_CODE, hook)
        try:
            self.call(0x112d0, eax=SRC, edx=fps, permitted_stop=CODE + 0x20abc)
        finally:
            self.mu.hook_del(handle)
        need(len(values) == 1, 'timer call was not observed')
        return values[0]

    def resource_directory(self, config):
        lines = config.splitlines(keepends=True)
        line_no, heap = 0, 0x660000
        calls = collections.Counter()
        stops = (0x2e354, 0x28aac, 0x2dad8, 0x22df0, 0x28d49, 0xba96)
        def hook(uc, address, size, user):
            nonlocal line_no, heap
            off = address - CODE
            calls[hex(off)] += 1
            if off == 0xba96:
                uc.emu_stop(); return
            if off == 0x28aac:
                need(self.cstr(self.get('EAX')).lower() == 'resource.cfg', 'wrong config source')
                self.set('EAX', 0x301000)
            elif off == 0x2dad8:
                dest, capacity = self.get('EAX'), self.get('EDX')
                need(line_no < 3 and len(lines[line_no]) < capacity, 'unexpected original fgets request')
                self.mu.mem_write(dest, lines[line_no] + b'\0'); line_no += 1
                self.set('EAX', dest)
            elif off == 0x22df0:
                size = self.get('EAX'); need(0 < size < 256, 'unexpected config allocation')
                self.set('EAX', heap); heap += (size + 15) // 16 * 16
            self.return_stub()
        handles = [self.mu.hook_add(self.uc.UC_HOOK_CODE, hook, begin=CODE+x, end=CODE+x) for x in stops]
        try:
            self.call(0xb962, eax=CTX, permitted_stop=CODE + 0xba96)
        finally:
            for h in handles:
                self.mu.hook_del(h)
        need(line_no == 3, 'original initializer did not consume three directory lines')
        prefix = self.cstr(self.read32(DATA + 0x22310))
        need(prefix.lower() == 'mov\\', 'unexpected original movie directory')
        return {'source': 'RESOURCE.CFG', 'source_sha256': sha(config), 'lines_read': line_no,
                'movie_directory': prefix, 'assignment_object1': 0xba89, 'stub_calls': dict(calls)}

    def startup_trace(self, skip_after_movie=0, skip_during_title=False):
        # The prefix was initialized by original code from pinned RESOURCE.CFG.
        need(self.cstr(self.read32(DATA + 0x22310)).lower() == 'mov\\', 'resource initializer missing')
        self.mu.mem_write(DATA + 0x42654, b'\0\0')
        events, movies, waits = [], [], []
        stubs = {0x112d0, 0x103ac, 0x26ef8, 0x273f8, 0x24188, 0x2d380,
                 0x27e50, 0x2cf14, 0x10498, 0x28e9e, 0x26f60, 0x21e06, 0x224d7}
        def hook(uc, address, size, user):
            if address == STOP or CODE + 0x10799 <= address <= CODE + 0x10918:
                return
            off = address - CODE
            need(off in stubs, f'unexpected original startup callee {off:#x}')
            if off == 0x112d0:
                item = {'event': 'movie', 'source': self.cstr(self.get('EAX')),
                        'fps': self.get('EDX'), 'caller_return': self.read32(self.get('ESP')) - CODE}
                movies.append(item); events.append(item)
                if skip_after_movie and len(movies) == skip_after_movie:
                    self.mu.mem_write(DATA + 0x42654, b'\1\0')
            elif off == 0x27e50:
                events.append({'event': 'title', 'source': self.cstr(self.get('EDX'))})
            elif off == 0x2d380:
                wait = self.get('EAX'); waits.append(wait)
                if skip_during_title and wait == 20:
                    self.mu.mem_write(DATA + 0x42654, b'\1\0')
            elif off == 0x28e9e:
                sp = self.get('ESP')
                dest, fmt, source = (self.read32(sp + i) for i in (4, 8, 12))
                value = self.cstr(fmt) % self.cstr(source)
                self.mu.mem_write(dest, value.encode('ascii') + b'\0')
            self.return_stub()
        handle = self.mu.hook_add(self.uc.UC_HOOK_CODE, hook)
        try:
            self.call(0x10799)
        finally:
            self.mu.hook_del(handle)
        return {'events': events, 'delay_arguments': dict(collections.Counter(waits)),
                'skip_after_movie': skip_after_movie, 'skip_during_title': skip_during_title,
                'stubbed_callees': sorted(hex(x) for x in stubs), 'scope': 'CALLER_CONTROL_FLOW_AND_ARGUMENTS_ONLY'}

    def title_canvas(self, pcx):
        from PIL import Image
        import io
        self.mu.mem_write(SRC, b'title.pcx\0')
        self.mu.mem_write(DST, b'\0' * (640 * 480))
        self.write32(0x301010, 1)
        self.write32(DATA + 0x6f58, 0)
        cursor, heap = 0, 0x660000
        calls = collections.Counter()
        services = (0x28aac, 0x28b42, 0x28b7f, 0x28d49, 0x22e90, 0x2e8e7, 0x22fa9, 0x23650)
        def hook(uc, address, size, user):
            nonlocal cursor, heap
            off = address - CODE
            calls[hex(off)] += 1
            if off == 0x28aac:
                cursor = 0; self.set('EAX', 0x301000)
            elif off == 0x28b42:
                self.set('EAX', len(pcx))
            elif off == 0x28b7f:
                dest, unit, count = self.get('EAX'), self.get('EDX'), self.get('EBX')
                need(unit > 0 and unit * count <= len(pcx), 'invalid original read request')
                value = pcx[cursor:cursor + unit * count]; cursor += len(value)
                self.mu.mem_write(dest, value); self.set('EAX', len(value) // unit)
            elif off in (0x22e90, 0x2e8e7):
                count = self.get('EAX'); need(0 < count < 0x10000, 'unexpected PCX allocation')
                self.set('EAX', heap); heap += (count + 15) // 16 * 16
                need(heap < 0x700000, 'PCX fixture heap exhausted')
            elif off == 0x23650:
                raise ValueError('original PCX decoder rejected the supplied corpus')
            self.return_stub()
        handles = [self.mu.hook_add(self.uc.UC_HOOK_CODE, hook, begin=CODE+x, end=CODE+x) for x in services]
        try:
            self.call(0x2ca90, eax=SRC, edx=DST, ebx=640, ecx=480, args=(0, 0))
        finally:
            for handle in handles:
                self.mu.hook_del(handle)
        result = bytes(self.mu.mem_read(DST, 640 * 480))
        with Image.open(io.BytesIO(pcx)) as source:
            need(source.mode == 'P' and source.size == (631, 474), 'unexpected PCX oracle geometry')
            pixels = source.tobytes()
        expected = bytearray(640 * 480)
        for y in range(474):
            expected[y * 640:y * 640 + 631] = pixels[y * 631:(y + 1) * 631]
        need(result == expected, 'native PCX canvas mismatch')
        return {'source': 'TITLE.PCX', 'source_sha256': sha(pcx), 'canvas': [640,480],
                'source_geometry': [631,474], 'placement': [0,0], 'indexed_canvas_sha256': sha(result),
                'matched_pixels': 640 * 480, 'file_service_calls': dict(calls),
                'scope': 'Original PCX instructions; file and allocator services are explicit fixture stubs'}

    def palette(self, payload):
        self.mu.mem_write(SRC, payload)
        self.mu.mem_write(DATA + 0x22896, b'\0\0')
        calls = []
        def hook(uc, address, size, user):
            if address == CODE + 0x255a8:
                calls.append(self.get('EAX')); self.return_stub()
        handle = self.mu.hook_add(self.uc.UC_HOOK_CODE, hook)
        try:
            self.call(0x10efc, eax=CTX, edx=SRC)
        finally:
            self.mu.hook_del(handle)
        need(calls == [DATA + 0x228b0], 'unexpected palette backend call')
        return bytes(self.mu.mem_read(DATA + 0x228b0, 768))

def validate(corpus: Path) -> dict:
    exe = (corpus / 'R.EXE').read_bytes()
    need(sha(exe) == EXE_SHA, 'original executable SHA mismatch')
    image = BoundLE.parse(exe)
    native = Native(image)
    results, total_frames = [], 0
    for name in reconstructed.FILES:
        raw = (corpus / name).read_bytes()
        need(sha(raw) == reconstructed.SOURCE_SHA[name], 'MOV source SHA mismatch')
        movie = reconstructed.decode_movie(raw)
        width, height = movie['header']['width'], movie['header']['height']
        size = width * height
        group = movie['groups'][0]
        packed = raw[group['offset'] + 16:group['end']]
        expected, stats = reconstructed.unpack_huffman(packed, group['raw_size'])
        native.mu.mem_write(SRC, packed + b'\0' * 16)
        native.call(0x1d748, args=(SRC, DST))
        native_huffman = bytes(native.mu.mem_read(DST, len(expected)))
        need(native_huffman == expected, 'native Huffman mismatch')
        native.setup_frame(width, height)
        hashes, consumption = [], []
        palette = b'\0' * 768
        for index, group in enumerate(movie['groups']):
            for packet in group['packets']:
                kind, payload = packet['type'], packet['data']
                if kind == 5:
                    palette = native.palette(payload)
                    need(palette == movie['frames'][index]['palette'], 'native VGA6 palette mismatch')
                if kind not in (1, 4):
                    continue
                native.mu.mem_write(SRC, payload + b'\0' * 16)
                native.call(0x10bfc if kind == 1 else 0x10c40, eax=CTX, edx=SRC)
                if kind == 4:
                    extra = native.get('EDX') - SRC - len(payload)
                    # Original implementation may prefetch the following mode byte.
                    need(extra in (0, 1), 'unexpected original delta consumption')
                    consumption.append(extra)
            actual = bytes(native.mu.mem_read(DST, size))
            need(actual == movie['frames'][index]['indices'], f'native indexed frame mismatch {name}:{index}')
            hashes.append(sha(actual + palette))
            # Execute the original image-copy routine, not a Python swap assumption.
            native.call(0x26f68, eax=D1, edx=D2)
            need(bytes(native.mu.mem_read(PREV, size)) == actual, 'original frame copy failed')
        total_frames += len(hashes)
        results.append({'source': name, 'source_sha256': sha(raw), 'frames': len(hashes),
                        'index_palette_frame_sha256': hashes, 'huffman_sha256': sha(native_huffman),
                        'huffman_bytes': len(native_huffman), 'delta_prefetch_histogram': dict(collections.Counter(consumption)),
                        'native_index_palette_equivalence': True})
        print(json.dumps({'source': name, 'frames': len(hashes), 'native_equivalence': 'PASS'}), flush=True)
    title_proof = native.title_canvas((corpus / 'TITLE.PCX').read_bytes())
    from intro_source_contract_v312 import RESOURCE_CFG_SHA
    config = (corpus / 'RESOURCE.CFG').read_bytes()
    need(sha(config) == RESOURCE_CFG_SHA, 'resource configuration SHA mismatch')
    directory_proof = native.resource_directory(config)
    startup = native.startup_trace()
    need([(x['source'].lower(), x.get('fps')) for x in startup['events']] ==
         [('mindlogo.mov', 15), ('intro.mov', 10), ('title.pcx', None), ('mov\\intro.mov', 10)], 'unexpected startup order')
    need(startup['delay_arguments'] == {30: 3, 20: 130}, 'unexpected startup wait loop')
    skips = [native.startup_trace(1), native.startup_trace(2), native.startup_trace(skip_during_title=True)]
    need([len([e for e in x['events'] if e['event'] == 'movie']) for x in skips] == [1, 2, 2], 'skip gates differ')
    periods = {str(fps): native.timer_period(fps) for fps in (15, 10)}
    need(periods == {'15': 66666, '10': 100000}, 'original timer period mismatch')
    return {'schema': 'openazrael.original_intro_mechanism.v312', 'status': 'MECHANISM_EQUIVALENCE_PASS',
            'exe_sha256': EXE_SHA, 'bound_le': image.report(), 'unicorn_version': native.version,
            'native_function_offsets': {'huffman': 'object1:0x1d748', 'keyframe': 'object1:0x10bfc',
               'delta': 'object1:0x10c40', 'copy': 'object1:0x26f68', 'palette': 'object1:0x10efc',
               'startup': 'object1:0x10799', 'play_movie': 'object1:0x112d0'},
            'native_calls': native.calls, 'frame_count': total_frames, 'movies': results,
            'resource_config': directory_proof, 'title_pcx': title_proof, 'startup': startup, 'skip_gate_traces': skips, 'timer_period_us': periods,
            'original_pcm_rate_instruction': {'object1_offset': '0x10fec', 'bytes': image.objects[0].data[0x10fec:0x10ff1].hex(), 'rate_argument_ebx': 22050},
            'not_verified': ['DOS/VGA full runtime', 'wall-clock timing under DOS', 'palette fade curves',
                             'DAC6-to-display-RGB expansion', 'physical audio-device latency', 'full Candidate fidelity']}

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('corpus', type=Path); ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--unicorn-path', type=Path)
    args = ap.parse_args()
    if args.unicorn_path:
        sys.path.insert(0, str(args.unicorn_path))
    report = validate(args.corpus)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
    print(json.dumps({'status': report['status'], 'frames': report['frame_count'], 'native_calls': report['native_calls']}))

if __name__ == '__main__':
    main()
