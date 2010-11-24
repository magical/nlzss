#!/usr/bin/env python3

import sys
from sys import stdin, stdout, stderr, exit
from os import SEEK_SET, SEEK_CUR, SEEK_END
from errno import EPIPE
from struct import pack, unpack

class DecompressionError(ValueError):
    pass

class VerificationError(ValueError):
    pass

def bits(byte):
    return ((byte >> 7) & 1,
            (byte >> 6) & 1,
            (byte >> 5) & 1,
            (byte >> 4) & 1,
            (byte >> 3) & 1,
            (byte >> 2) & 1,
            (byte >> 1) & 1,
            (byte) & 1)

def decompress_raw_lzss10(indata, decompressed_size, _overlay=False):
    """Decompress LZSS-compressed bytes. Returns a bytearray."""
    data = bytearray()

    it = iter(indata)

    if _overlay:
        disp_extra = 3
    else:
        disp_extra = 1

    def writebyte(b):
        data.append(b)
    def readbyte():
        return next(it)
    def readshort():
        # big-endian
        a = next(it)
        b = next(it)
        return (a << 8) | b
    def copybyte():
        data.append(next(it))

    while len(data) < decompressed_size:
        b = readbyte()
        if b == 0:
            # dumb optimization
            for _ in range(8):
                copybyte()
            continue
        flags = bits(b)
        for flag in flags:
            if flag == 0:
                copybyte()
            elif flag == 1:
                sh = readshort()
                count = (sh >> 0xc) + 3
                disp = (sh & 0xfff) + disp_extra

                for _ in range(count):
                    writebyte(data[-disp])
            else:
                raise ValueError(flag)

            if decompressed_size <= len(data):
                break

    if len(data) != decompressed_size:
        raise DecompressionError("decompressed size does not match the expected size")

    return data

def lz11_tokens(indata):
    it = iter(indata)
    i = 4

    def readbyte():
        nonlocal i
        i += 1
        return next(it)

    while True:
        flagpos = i
        flags = bits(readbyte())
        for flag in flags:
            pos = i
            if flag == 0:
                yield readbyte(), pos, flagpos
            elif flag == 1:
                b = readbyte()
                indicator = b >> 4

                if indicator == 0:
                    # 8 bit count, 12 bit disp
                    # indicator is 0, don't need to mask b
                    count = (b << 4)
                    b = readbyte()
                    count += b >> 4
                    count += 0x11
                elif indicator == 1:
                    # 16 bit count, 12 bit disp
                    count = ((b & 0xf) << 12) + (readbyte() << 4)
                    b = readbyte()
                    count += b >> 4
                    count += 0x111
                else:
                    # indicator is count (4 bits), 12 bit disp
                    count = indicator
                    count += 1

                disp = ((b & 0xf) << 8) + readbyte()
                disp += 1

                yield (count, -disp), pos, flagpos
            else:
                raise ValueError(flag)

def verify(obj):
    """Verify LZSS-compressed bytes or a file-like object.

    Shells out to verify_file() or verify_bytes() depending on
    whether or not the passed-in object has a 'read' attribute or not.

    Returns None on success. Raises an exception on error."""
    if hasattr(obj, 'read'):
        return verify_file(obj)
    else:
        return verify_bytes(obj)

def verify_bytes(data):
    """Verify LZSS-compressed bytes.

    Returns None on success. Raises an exception on error.
    """
    header = data[:4]
    if header[0] == 0x10:
        tokenize = lz10_tokens
    elif header[0] == 0x11:
        tokenize = lz11_tokens
    else:
        raise VerificationError("not as lzss-compressed file")

    decompressed_size, = unpack("<L", header[1:] + b'\x00')

    data = data[4:]
    tokens = tokenize(data, decompressed_size)
    return verify_tokens(tokens)

def verify_file(f):
    """Verify an LZSS-compressed file.

    Returns None on success. Raises an exception on error.
    """
    header = f.read(4)
    if header[0] == 0x10:
        tokenize = lz10_tokens
    elif header[0] == 0x11:
        tokenize = lz11_tokens
    else:
        raise VerificationError("not as lzss-compressed file")

    decompressed_size, = unpack("<L", header[1:] + b'\x00')

    data = f.read()
    tokens = tokenize(data)
    return verify_tokens(tokens, decompressed_size)

def verify_tokens(tokens, decompressed_length):
    length = 0
    for t in tokens:
        t, pos, flagpos = t
        if type(t) == tuple:
            count, disp = t
            assert disp < 0
            assert 0 < count
            if disp + length < 0:
                raise VerificationError(
                    "disp too large. length: {:#x}, disp: {:#x}, pos: {:#x}, flagpos: {:#x}"
                    .format(length, disp, pos, flagpos))
            length += count
        else:
            length += 1

        if length >= decompressed_length:
            break

    if length != decompressed_length:
        raise VerificationError(
            "decompressed size does not match. got: {:#x}, expected: {:#x}".format(
                length, decompressed_length))

def dump_file(f):
    header = f.read(4)
    if header[0] == 0x10:
        tokenize = lz10_tokens
    elif header[0] == 0x11:
        tokenize = lz11_tokens
    else:
        raise VerificationError("not as lzss-compressed file")

    decompressed_size, = unpack("<L", header[1:] + b'\x00')

    data = f.read()
    tokens = tokenize(data)
    def dump():
        for t, pos, flagpos in tokens:
            if type(t) == tuple:
                yield t
    from pprint import pprint
    pprint(list(dump()))

def main(args=None):
    if args is None:
        args = sys.argv[1:]

    if '--overlay' in args:
        args.remove('--overlay')
        overlay = True
    else:
        overlay = False

    if len(args) < 1 or args[0] == '-':
        if overlay:
            print("Can't verify overlays from stdin", file=stderr)
            return 2

        if hasattr(stdin, 'detach'):
            f = stdin.detach()
        else:
            f = stdin
    else:
        try:
            f = open(args[0], "rb")
        except IOError as e:
            print(e, file=stderr)
            return 2

    try:
        if overlay:
            print("Can't verify overlays", file=stderr)
        else:
            #verify_file(f)
            dump_file(f)
    except (VerificationError,) as e:
        print(e, file=stderr)
        return 1

    return 0



if __name__ == '__main__':
    exit(main())
