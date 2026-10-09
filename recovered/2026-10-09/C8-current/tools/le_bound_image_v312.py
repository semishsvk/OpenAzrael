#!/usr/bin/env python3
"""Bound-MZ/LE image reader with explicit file/module/header/object coordinates.

Only internal 32-bit-offset fixups are supported, including source lists and
signed page-relative offsets. Unsupported forms fail closed. No corpus writes.
Old v27 raw fixups were not the root cause: LE-relative data-page extraction
was wrong for the bound demo. Never add an unexplained global offset to fixups.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import argparse, collections, hashlib, json, re, struct

class LEError(ValueError):
    pass

def need(ok: bool, message: str) -> None:
    if not ok:
        raise LEError(message)

def unpack(fmt: str, data: bytes, offset: int):
    size = struct.calcsize(fmt)
    need(0 <= offset <= len(data) - size, f"truncated {fmt} at {offset:#x}")
    return struct.unpack_from(fmt, data, offset)

def u32(data: bytes, offset: int) -> int:
    return unpack('<I', data, offset)[0]

@dataclass(frozen=True)
class Object:
    number: int
    size: int
    base: int
    flags: int
    first_page: int
    page_count: int
    data: bytes
    pages: tuple

@dataclass(frozen=True)
class Fixup:
    page: int
    record_file_offset: int
    raw_hex: str
    source_list: bool
    source_object: int
    source_page_offset: int
    source_offset: int
    target_object: int
    target_offset: int

@dataclass
class BoundLE:
    raw: bytes
    module_file_offset: int
    header_file_offset: int
    page_size: int
    data_file_offset: int
    objects: list[Object]
    fixups: list[Fixup]
    records: int
    pages_total: int

    @classmethod
    def parse(cls, raw: bytes) -> 'BoundLE':
        need(0xC4 <= len(raw) <= 64 * 1024 * 1024, 'unsupported executable size')
        candidates = [(0, 0)] if raw[:2] == b'LE' else []
        for match in re.finditer(b'MZ', raw):
            mz = match.start()
            if mz + 0x40 > len(raw):
                continue
            distance = u32(raw, mz + 0x3C)
            le = mz + distance
            if distance >= 0x40 and raw[le:le + 2] == b'LE':
                candidates.append((mz, le))
        need(len(candidates) == 1, f'expected one bound LE header; found {len(candidates)}')
        module, header = candidates[0]
        need(header + 0xC4 <= len(raw), 'short LE header')
        need(raw[header + 2:header + 4] == b'\0\0', 'non-little-endian LE')
        h = lambda offset: u32(raw, header + offset)
        count, page_size, last_size = h(0x14), h(0x28), h(0x2C)
        need(1 <= count <= 32768 and 16 <= page_size <= 65536, 'invalid page geometry')
        need(page_size & (page_size - 1) == 0 and 1 <= last_size <= page_size, 'invalid last page')
        ot, oc, pm = header + h(0x40), h(0x44), header + h(0x48)
        need(1 <= oc <= 64 and ot + 24 * oc <= len(raw), 'invalid object table')
        need(pm + count * 4 <= len(raw), 'truncated page map')
        # Unlike table offsets, data pages are relative to the containing MZ module.
        data_start = module + h(0x80)
        need(header < data_start < len(raw), 'invalid module-relative data start')
        objects, ownership = [], {}
        total_virtual = 0
        for index in range(oc):
            size, base, flags, first, npages, reserved = unpack('<6I', raw, ot + index * 24)
            need(0 < size <= 64 * 1024 * 1024 and 0 < first <= count + 1, 'invalid object')
            need(first - 1 + npages <= count, 'object page range outside page map')
            need(base + size <= 128 * 1024 * 1024, 'oversized linear address range')
            total_virtual += size
            need(total_virtual <= 128 * 1024 * 1024, 'oversized virtual image')
            image = bytearray(size)
            pages = []
            for local in range(npages):
                gp = first - 1 + local
                need(gp not in ownership, 'overlapping object page ownership')
                ownership[gp] = (index + 1, local * page_size)
                ent = raw[pm + gp * 4:pm + gp * 4 + 4]
                physical = int.from_bytes(ent[:3], 'big')
                page_flag = ent[3]
                need(page_flag in (0, 3), f'unsupported LE page flag {page_flag}')
                if page_flag == 3:
                    pages.append((gp + 1, physical, None, 0))
                    continue
                need(1 <= physical <= count, 'invalid physical page number')
                file_off = data_start + (physical - 1) * page_size
                n = last_size if physical == count else page_size
                need(file_off + n <= len(raw), 'truncated physical page')
                dst = local * page_size
                need(dst < size, 'page outside virtual object')
                copied = min(n, size - dst)
                image[dst:dst + copied] = raw[file_off:file_off + copied]
                pages.append((gp + 1, physical, file_off, n))
            objects.append(Object(index + 1, size, base, flags, first, npages, bytes(image), tuple(pages)))
        fpt, frt = header + h(0x68), header + h(0x6C)
        need(fpt + (count + 1) * 4 <= frt <= data_start, 'invalid fixup table layout')
        page_offsets = [u32(raw, fpt + i * 4) for i in range(count + 1)]
        need(page_offsets[0] == 0 and page_offsets == sorted(page_offsets), 'invalid fixup page offsets')
        need(frt + page_offsets[-1] <= data_start, 'fixups overlap data pages')
        fixups, record_count = [], 0
        for page in range(count):
            p, end = frt + page_offsets[page], frt + page_offsets[page + 1]
            need(page in ownership or p == end, 'fixup page has no owning object')
            while p < end:
                start = p
                need(p + 3 <= end, 'truncated fixup header')
                st, fl = raw[p:p + 2]; p += 2
                need(st in (0x07, 0x27), f'unsupported source type {st:#x}')
                need(fl in (0, 0x10, 0x40, 0x50), f'unsupported target flags {fl:#x}')
                is_list = bool(st & 0x20)
                if is_list:
                    nsource = raw[p]; p += 1
                    need(nsource > 0, 'empty source list')
                    sources = []
                else:
                    need(p + 2 <= end, 'short source offset')
                    sources = list(unpack('<h', raw, p)); p += 2
                    nsource = 0
                ordinal_size = 2 if fl & 0x40 else 1
                target_size = 4 if fl & 0x10 else 2
                need(p + ordinal_size + target_size + nsource * 2 <= end, 'fixup crosses record page boundary')
                target_object = int.from_bytes(raw[p:p + ordinal_size], 'little'); p += ordinal_size
                target_offset = int.from_bytes(raw[p:p + target_size], 'little'); p += target_size
                if is_list:
                    sources = list(unpack('<' + 'h' * nsource, raw, p)); p += nsource * 2
                need(1 <= target_object <= oc, 'invalid target object')
                need(target_offset < objects[target_object - 1].size, 'target outside virtual object')
                so, page_base = ownership[page]
                for relative in sources:
                    source_off = page_base + relative
                    need(-3 <= relative < page_size, 'invalid signed source offset')
                    need(0 <= source_off <= objects[so - 1].size - 4, 'source outside virtual object')
                    fixups.append(Fixup(page + 1, start, raw[start:p].hex(), is_list, so,
                                        relative, source_off, target_object, target_offset))
                record_count += 1
            need(p == end, 'fixup page not consumed exactly')
        seen = {}
        for r in fixups:
            key, target = (r.source_object, r.source_offset), (r.target_object, r.target_offset)
            need(key not in seen or seen[key] == target, 'conflicting duplicate relocation')
            seen[key] = target
        return cls(raw, module, header, page_size, data_start, objects, fixups, record_count, count)

    def fixup_at(self, object_no: int, offset: int) -> Fixup:
        hits = [r for r in self.fixups if (r.source_object, r.source_offset) == (object_no, offset)]
        need(bool(hits), f'no relocation at object {object_no}:{offset:#x}')
        return hits[0]

    def relocated_objects(self) -> list[bytes]:
        buffers = [bytearray(o.data) for o in self.objects]
        for r in self.fixups:
            value = self.objects[r.target_object - 1].base + r.target_offset
            struct.pack_into('<I', buffers[r.source_object - 1], r.source_offset, value)
        return [bytes(b) for b in buffers]

    def report(self) -> dict:
        matched = sum(u32(self.objects[r.source_object - 1].data, r.source_offset) == r.target_offset for r in self.fixups)
        return {'schema': 'openazrael.bound_le.v312', 'exe_sha256': hashlib.sha256(self.raw).hexdigest(),
                'module_file_offset': self.module_file_offset, 'header_file_offset': self.header_file_offset,
                'data_file_offset': self.data_file_offset, 'header_relative_data_error': self.header_file_offset - self.module_file_offset,
                'page_size': self.page_size, 'pages': self.pages_total, 'raw_records': self.records,
                'expanded_fixups': len(self.fixups), 'source_list_references': sum(r.source_list for r in self.fixups),
                'raw_operand_target_matches': matched, 'negative_page_sources': sum(r.source_page_offset < 0 for r in self.fixups),
                'objects': [{'number': o.number, 'base': o.base, 'size': o.size, 'first_page': o.first_page,
                             'page_count': o.page_count, 'sha256': hashlib.sha256(o.data).hexdigest()} for o in self.objects]}

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('exe', type=Path); ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    image = BoundLE.parse(args.exe.read_bytes())
    report = image.report()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    main()
