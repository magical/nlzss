#!/usr/bin/env python3

from lzss3 import (decompress_raw_lzss10, decompress_raw_lzss11,
                   decompress_overlay, decompress)
from compress import _compress, compress, compress_nlz11, NLZ11Window

from io import BytesIO

def test_lzss10():
    assert decompress_raw_lzss10(b'\x00', 0) == b''
    assert decompress_raw_lzss10(b'\x00abcdefgh', 8) == b'abcdefgh'
    assert decompress_raw_lzss10(b'\x08abcd\xd0\x03', 20) == b'abcd' * 5

def test_lzss11():
    assert decompress_raw_lzss11(b'\x00', 0) == b''
    assert decompress_raw_lzss11(b'\x00abcdefgh', 8) == b'abcdefgh'
    assert decompress_raw_lzss11(b'\x08abcd\xf0\x03', 20) == b'abcd' * 5
    assert decompress_raw_lzss11(b'\x08abcd\x01\x30\x03', 40) == b'abcd' * 10
    assert decompress_raw_lzss11(b'\x08abcd\x10\x07\xb0\x03', 400) == b'abcd' * 100

def test_overlay():
    in_ = BytesIO(b'\x01\xd0abcd\x08\xff\x10\x00\x00\x09\x04\x00\x00\x00')
    out = BytesIO()
    decompress_overlay(in_, out)
    assert out.getvalue() == b'abcd' * 5

def test_compress():
    assert list(_compress(b'abcdabcd')) == [97, 98, 99, 100, (4, -4)]
    assert list(_compress(b'xaaabaaaaa')) == [120, 97, 97, 97, 98, (3, -4), 97, 97]

    assert list(_compress(b'a' + b'b' * 4095 + b'abb'))[-1] == (3, -4096)
    assert list(_compress(b'a' + b'b' * 4096 + b'abb'))[-1] == 98

    #print( list(_compress(b'abcdefg' * 10)) )
    assert list(_compress(b'abcdefg' * 10)) == \
        [97, 98, 99, 100, 101, 102, 103, (18, -7), (18, -21), (18, -42), (9, -56)]

    assert list(_compress(b'abcdefg' * 10, NLZ11Window)) == \
        [97, 98, 99, 100, 101, 102, 103, (63, -7)]

    out = BytesIO()
    compress_nlz11(b'abcdefg' * 10, out)
    assert out.getvalue()[12:15] == b'\x02\xe0\x06'

def test_roundtrip():
    #assert False
    with open("lzss3.py", "rb") as f:
        indata = f.read()
    out = BytesIO()
    compress(indata, out)
    compressed_data = out.getvalue()
    assert len(compressed_data) < len(indata)

    decompressed_data = decompress(out.getvalue())
    assert indata == decompressed_data


    #same as above, but with lz11
    out = BytesIO()
    compress_nlz11(indata, out)
    compressed_data = out.getvalue()
    assert len(compressed_data) < len(indata)

    decompressed_data = decompress(out.getvalue())
    assert indata == decompressed_data

if __name__ == '__main__':
    test_lzss10()
    test_lzss11()
    test_overlay()
    test_compress()
    test_roundtrip()
