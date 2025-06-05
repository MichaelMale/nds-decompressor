import os
import sqlite3
import tempfile
import unittest
import zlib

from nds_decompressor import (
    decompress_nds,
    SLOT_HEADER_SIZE,
    PAGE_MAP_START,
)

class TestNds(unittest.TestCase):
    def _create_sqlite_db(self, path: str) -> bytes:
        conn = sqlite3.connect(path)
        conn.execute("PRAGMA page_size=4096")
        conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, data TEXT)")
        conn.execute("INSERT INTO t (data) VALUES ('hello')")
        conn.commit()
        conn.close()
        with open(path, 'rb') as f:
            return f.read()

    def _build_nds_file(self, db_bytes: bytes, nds_path: str) -> None:
        slot_payload = zlib.compress(db_bytes)
        slot = b"\x00" * SLOT_HEADER_SIZE + slot_payload
        data_start = PAGE_MAP_START + 8
        data_end = data_start + len(slot)

        header = bytearray(200)
        header[:2] = b"ZV"
        header[108:116] = data_start.to_bytes(8, 'big')
        header[116:124] = data_end.to_bytes(8, 'big')
        header[140:148] = len(db_bytes).to_bytes(8, 'big')
        header[172:176] = (4096).to_bytes(4, 'big')
        header[176:180] = (1).to_bytes(4, 'big')

        page_map = bytearray()
        page_map += data_start.to_bytes(5, 'big')
        tmp = (len(slot) << 7)
        page_map += tmp.to_bytes(3, 'big')

        with open(nds_path, 'wb') as f:
            f.write(header)
            f.write(page_map)
            f.write(slot)

    def test_decompress_valid_nds(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, 'db.sqlite')
            nds_path = os.path.join(tmpdir, 'db.nds')
            db_bytes = self._create_sqlite_db(db_path)
            self._build_nds_file(db_bytes, nds_path)

            output = decompress_nds(nds_path)
            self.assertTrue(os.path.exists(output))

            conn = sqlite3.connect(output)
            row = conn.execute('SELECT data FROM t WHERE id=1').fetchone()
            conn.close()
            self.assertEqual(row[0], 'hello')

    def test_invalid_header(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            nds_path = os.path.join(tmpdir, 'bad.nds')
            with open(nds_path, 'wb') as f:
                f.write(b'not an nds file')

            with self.assertRaises(ValueError):
                decompress_nds(nds_path)

if __name__ == '__main__':
    unittest.main()
