# nds-decompressor

A Python 3.9 implementation for decompressing Navigation Data Standard (NDS)
ZipVFS databases.

Given an NDS file it verifies the `ZV` magic header, parses the ZipVFS page map
and uses the built in `zlib` module to decompress all pages into a regular
SQLite database file.

## Usage

```bash
python nds_decompressor.py example.nds output.sqlite
```

If the output file is omitted it will create `example.nds.sqlite` in the same
directory.

## Running Tests

Use Python's unittest discovery to run the automated tests:

```bash
python -m unittest -v
```
