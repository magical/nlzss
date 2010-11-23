#!/usr/bin/env python3

from lzss3 import (decompress_raw_lzss10, decompress_raw_lzss11,
                   decompress_overlay)

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
    from io import BytesIO
    in_ = BytesIO(b'\x01\xd0abcd\x08\xff\x10\x00\x00\x09\x04\x00\x00\x00')
    out = BytesIO()
    decompress_overlay(in_, out)
    assert out.getvalue() == b'abcd' * 5

if __name__ == '__main__':
    test_lzss10()
    test_lzss11()
    test_overlay()
