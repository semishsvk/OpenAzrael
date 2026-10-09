#!/usr/bin/env python3
"""Independent synthetic framing tests plus all eight instruction operand anchors."""
import hashlib, json, os, struct, unittest
from pathlib import Path
from le_bound_image_v312 import BoundLE, LEError, u32

EXE_SHA = '381e4f5c61e4bb8c27f06b1944e6673bbebc39ca219cc08fb9f948da2ca37c00'
ANCHORS = {0xcf4d: '94190000', 0xcf7e: '5e610000', 0xd005: '54190000',
           0xd00b: '5c190000', 0xd01e: '64190000', 0xd05b: '54190000',
           0xd061: '5c190000', 0xd074: '64190000'}

def fixture(records=(b'',), page_numbers=None, data_words=()):
    n = len(records); mz = 0x100; le = mz + 0x80; data_start = mz + 0x1000
    b = bytearray(data_start + 4096 * n)
    b[mz:mz + 2] = b'MZ'; struct.pack_into('<I', b, mz + 0x3c, 0x80)
    b[le:le + 2] = b'LE'
    pm = 0xc4 + 24; fpt = pm + n * 4; frt = fpt + (n + 1) * 4
    for o, v in {0x14: n, 0x28: 4096, 0x2c: 4096, 0x40: 0xc4, 0x44: 1,
                 0x48: pm, 0x68: fpt, 0x6c: frt, 0x80: 0x1000}.items():
        struct.pack_into('<I', b, le + o, v)
    struct.pack_into('<6I', b, le + 0xc4, n * 4096, 0x10000, 0x2045, 1, n, 0)
    page_numbers = page_numbers or list(range(1, n + 1))
    for i, pn in enumerate(page_numbers):
        b[le + pm + i * 4:le + pm + i * 4 + 4] = pn.to_bytes(3, 'big') + b'\0'
    position = 0
    for i, recs in enumerate(records):
        struct.pack_into('<I', b, le + fpt + i * 4, position)
        b[le + frt + position:le + frt + position + len(recs)] = recs
        position += len(recs)
    struct.pack_into('<I', b, le + fpt + n * 4, position)
    for off, value in data_words:
        struct.pack_into('<I', b, data_start + off, value)
    return b

def single(src=4, target=32, flags=0x10):
    return bytes((7, flags)) + struct.pack('<hB', src, 1) + struct.pack('<I' if flags & 16 else '<H', target)

def proof(image):
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True
    error = image.header_file_offset - image.module_file_offset
    code = image.objects[0].data
    insns = list(md.disasm(code[0xcde1 + error:0xd090 + error], 0xcde1 + error))
    references = []
    for legacy, expected in ANCHORS.items():
        actual = legacy + error
        matches = [i for i in insns if i.disp_size == 4 and i.address + i.disp_offset == actual]
        if len(matches) != 1:
            raise AssertionError(f'not an independent disp32 operand: {actual:#x}')
        insn = matches[0]; fix = image.fixup_at(1, actual)
        assert code[actual:actual + 4].hex() == expected
        assert fix.target_object == 2 and fix.target_offset == int.from_bytes(bytes.fromhex(expected), 'little')
        references.append({'legacy_shifted_view_offset': legacy, 'canonical_object1_offset': actual,
                           'instruction_offset': insn.address, 'instruction_hex': insn.bytes.hex(),
                           'instruction': insn.mnemonic + ' ' + insn.op_str,
                           'operand_size': insn.disp_size, 'raw_operand': expected,
                           'fixup_file_offset': fix.record_file_offset, 'fixup_raw': fix.raw_hex,
                           'target_object': fix.target_object, 'target_offset': fix.target_offset})
    jump = list(md.disasm(code[0x1b1c6:0x1b1ce], 0x1b1c6))
    assert len(jump) == 1 and jump[0].mnemonic == 'jmp'
    assert image.fixup_at(1, jump[0].address + jump[0].disp_offset).target_offset == 0x1b09c
    dispatch = []
    for opcode in range(41):
        entry = 0x1b09c + opcode * 4
        fix = image.fixup_at(1, entry)
        assert fix.target_object == 1 and u32(code, entry) == fix.target_offset
        first = next(md.disasm(code[fix.target_offset:fix.target_offset + 16], fix.target_offset))
        dispatch.append({'opcode': opcode, 'entry_offset': entry, 'handler_offset': fix.target_offset,
                         'fixup_file_offset': fix.record_file_offset, 'handler_first_instruction': first.mnemonic + ' ' + first.op_str})
    assert dispatch[0x17]['handler_offset'] == 0x1b51e
    assert dispatch[0x18]['handler_offset'] == 0x1b6fc
    return {'anchors': references, 'dispatch': dispatch, 'status': 'EIGHT_INSTRUCTION_REFERENCES_PASS',
            'root_cause': 'DATA_PAGES_RELATIVE_TO_CONTAINING_MZ_MODULE_NOT_LE_HEADER',
            'fixup_record_parser_diagnosis': 'Old v27 raw sources agree with corrected object bytes. Do not offset raw fixups.',
            'historical_coordinate_policy': 'Tag old offsets as legacy_shifted_view; do not silently rewrite prior evidence.'}

class Synthetic(unittest.TestCase):
    def test_module_origin(self):
        x = BoundLE.parse(fixture(data_words=((0, 0xaabbccdd),)))
        self.assertEqual(x.module_file_offset, 0x100); self.assertEqual(x.header_file_offset, 0x180)
        self.assertEqual(u32(x.objects[0].data, 0), 0xaabbccdd)
    def test_single(self):
        x = BoundLE.parse(fixture((single(),), data_words=((4, 32),)))
        self.assertEqual(x.report()['raw_operand_target_matches'], 1)
        self.assertEqual(u32(x.relocated_objects()[0], 4), 0x10020)
    def test_target16(self):
        x = BoundLE.parse(fixture((single(flags=0),)))
        self.assertEqual(x.fixups[0].target_offset, 32)
    def test_ordinal16(self):
        rec = b'\x07\x50' + struct.pack('<hHI', 4, 1, 32)
        self.assertEqual(BoundLE.parse(fixture((rec,))).fixups[0].target_object, 1)
    def test_source_list(self):
        rec = b'\x27\x10\x03\x01' + struct.pack('<I3h', 32, 4, 8, 12)
        x = BoundLE.parse(fixture((rec,), data_words=((4,32),(8,32),(12,32))))
        self.assertEqual([f.source_offset for f in x.fixups], [4,8,12])
        self.assertEqual(x.records, 1); self.assertEqual(x.report()['source_list_references'], 3)
    def test_signed_cross_page(self):
        x = BoundLE.parse(fixture((single(4094), single(-2)), data_words=((4094,32),)))
        self.assertEqual([f.source_offset for f in x.fixups], [4094,4094])
        self.assertEqual(x.fixups[1].source_page_offset, -2)
    def test_negative_outside_object(self):
        with self.assertRaises(LEError): BoundLE.parse(fixture((single(-2),)))
    def test_conflicting_duplicate(self):
        with self.assertRaises(LEError): BoundLE.parse(fixture((single(4,32) + single(4,40),)))
    def test_physical_page_map(self):
        x = BoundLE.parse(fixture((b'',b''), page_numbers=[2,1], data_words=((0,11),(4096,22))))
        self.assertEqual([u32(x.objects[0].data, off) for off in (0,4096)], [22,11])
    def test_zero_fill_page(self):
        b=fixture(); b[0x180 + 0xdc + 3] = 3
        self.assertEqual(set(BoundLE.parse(b).objects[0].data), {0})
    def test_bad_page_flag(self):
        b=fixture(); b[0x180 + 0xdc + 3] = 2
        with self.assertRaises(LEError): BoundLE.parse(b)
    def test_unsupported_target(self):
        with self.assertRaises(LEError): BoundLE.parse(fixture((single(flags=0x11),)))
    def test_truncated_record(self):
        with self.assertRaises(LEError): BoundLE.parse(fixture((single()[:-1],)))
    def test_truncated_page(self):
        with self.assertRaises(LEError): BoundLE.parse(fixture()[:-1])
    def test_target_out_of_object(self):
        with self.assertRaises(LEError): BoundLE.parse(fixture((single(target=4096),)))
    def test_empty_source_list(self):
        with self.assertRaises(LEError): BoundLE.parse(fixture((b'\x27\x10\0\1'+struct.pack('<I',32),)))
    def test_ambiguous_header(self):
        b=fixture(); b[0:2]=b'MZ';struct.pack_into('<I',b,0x3c,0x180)
        with self.assertRaises(LEError): BoundLE.parse(b)
    def test_missing_header(self):
        b=fixture();b[0x100:0x102]=b'XX'
        with self.assertRaises(LEError): BoundLE.parse(b)
    def test_source_list_crosses_boundary(self):
        with self.assertRaises(LEError):BoundLE.parse(fixture((b'\x27\x10\3\1'+struct.pack('<Ih',32,4),)))
    def test_nonmonotonic_table(self):
        b=fixture((single(),single()));fpt=0xdc+8
        struct.pack_into('<I',b,0x180+fpt+8,1)
        with self.assertRaises(LEError):BoundLE.parse(b)

class Corpus(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get('OPENAZRAEL_CORPUS')
        if not path: raise unittest.SkipTest('set OPENAZRAEL_CORPUS for original executable tests')
        cls.raw=(Path(path)/'R.EXE').read_bytes()
        assert hashlib.sha256(cls.raw).hexdigest()==EXE_SHA
        cls.image=BoundLE.parse(cls.raw)
    def test_exact_eight_instruction_anchors(self):
        self.assertEqual(len(proof(self.image)['anchors']),8)
    def test_every_relocation(self):
        report=self.image.report()
        self.assertEqual(report['expanded_fixups'],28547)
        self.assertEqual(report['raw_operand_target_matches'],28547)
        self.assertEqual(report['source_list_references'],0)
        self.assertEqual(report['negative_page_sources'],20)
    def test_last_page_exact_eof(self):
        _,_,offset,size=self.image.objects[-1].pages[-1]
        self.assertEqual(offset+size,len(self.raw))
    def test_correct_origin(self):
        self.assertEqual(self.image.header_file_offset-self.image.module_file_offset,0x2aa8)
        self.assertEqual(self.image.data_file_offset,0x6f6a4)
    def test_legacy_wrong_origin_fails(self):
        old=self.image.raw[self.image.data_file_offset+0x2aa8:]
        self.assertNotEqual(old[:8],self.image.objects[0].data[:8])
        # Do not mistake legacy-view address cf4d for a canonical instruction operand.
        self.assertFalse(any(r.source_object==1 and r.source_offset==0xcf4d for r in self.image.fixups))

if __name__=='__main__': unittest.main(verbosity=2)
