import zlib
from dataclasses import dataclass
from typing import List

SLOT_HEADER_SIZE = 6
PAGE_MAP_START = 200  # 0xC8


def _read_uint_be(b: bytes, offset: int, length: int) -> int:
    """Read an unsigned big endian integer from a bytes object."""
    return int.from_bytes(b[offset:offset + length], byteorder='big')


@dataclass
class ZipVfsPageInfo:
    offset: int
    size: int
    unused_bytes: int

    @classmethod
    def from_bytes(cls, b: bytes, offset: int) -> 'ZipVfsPageInfo':
        if len(b) - offset < 8:
            raise ValueError("Buffer too small for ZipVfsPageInfo")
        page_offset = _read_uint_be(b, offset, 5)
        tmp = _read_uint_be(b, offset + 5, 3)
        page_size = tmp >> 7
        unused = tmp & 0x7F
        return cls(page_offset, page_size, unused)


@dataclass
class ZipVfsHeader:
    data_start: int
    data_end: int
    db_size: int
    page_size: int
    version: int
    page_map: List[ZipVfsPageInfo]

    @classmethod
    def from_bytes(cls, b: bytes) -> 'ZipVfsHeader':
        if len(b) < PAGE_MAP_START:
            raise ValueError("Header must be at least 200 bytes")
        data_start = _read_uint_be(b, 108, 8)
        data_end = _read_uint_be(b, 116, 8)
        db_size = _read_uint_be(b, 140, 8)
        page_size = _read_uint_be(b, 172, 4)
        version = _read_uint_be(b, 176, 4)
        return cls(data_start, data_end, db_size, page_size, version, [])

    def init_page_map(self, b: bytes) -> None:
        self.page_map = []
        for i in range(0, len(b), 8):
            if i + 8 > len(b):
                break
            pi = ZipVfsPageInfo.from_bytes(b, i)
            if pi.offset == 0:
                break
            self.page_map.append(pi)


def decompress_nds(src_path: str, dest_path: str = None) -> str:
    """Decompress an NDS/ZipVFS file to an SQLite database file."""
    if dest_path is None:
        dest_path = src_path + '.sqlite'

    with open(src_path, 'rb') as f:
        header = f.read(PAGE_MAP_START)
        if len(header) < PAGE_MAP_START:
            raise ValueError('File too small to be a valid NDS file')
        if not header.startswith(b'ZV'):
            raise ValueError('File does not appear to be a ZipVFS/NDS file')

        zh = ZipVfsHeader.from_bytes(header)
        page_map_len = zh.data_start - PAGE_MAP_START
        page_map_bytes = f.read(page_map_len)
        if len(page_map_bytes) != page_map_len:
            raise ValueError('Truncated page map')
        zh.init_page_map(page_map_bytes)

        with open(dest_path, 'wb') as out:
            for page in zh.page_map:
                f.seek(page.offset)
                data = f.read(page.size)
                if len(data) < page.size:
                    raise ValueError(f'Truncated page at offset {page.offset}')
                if len(data) < SLOT_HEADER_SIZE:
                    continue
                if not (len(data) >= SLOT_HEADER_SIZE + 2 and data[SLOT_HEADER_SIZE] == 0x78 and data[SLOT_HEADER_SIZE + 1] in (0x01, 0x9C, 0xDA)):
                    # not a zlib stream
                    continue
                try:
                    decompressed = zlib.decompress(data[SLOT_HEADER_SIZE:])
                except zlib.error:
                    continue
                out.write(decompressed)

    return dest_path


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Decompress NDS ZipVFS database')
    parser.add_argument('source', help='Input NDS file')
    parser.add_argument('destination', nargs='?', help='Output SQLite file')
    args = parser.parse_args()

    output = decompress_nds(args.source, args.destination)
    print(f'Decompressed file written to {output}')
