#!/usr/bin/env python3

import sys
from sys import argv, stdout
from os import SEEK_SET, SEEK_CUR, SEEK_END
from errno import EPIPE
from struct import pack, unpack

def bits(byte):
    return ((byte >> 7) & 1,
            (byte >> 6) & 1,
            (byte >> 5) & 1,
            (byte >> 4) & 1,
            (byte >> 3) & 1,
            (byte >> 2) & 1,
            (byte >> 1) & 1,
            (byte) & 1)

def decompress(indata, decompressed_size):
    """Decompress LZSS-compressed bytes. Returns a bytearray."""
    data = bytearray()

    it = iter(indata)

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
                try:
                    copybyte()
                except StopIteration:
                    return data
            elif flag == 1:
                sh = readshort()
                count = (sh >> 0xc) + 3
                # +3 for overlays
                # +1 for files
                disp = (sh & 0xfff) + 3

                for _ in range(count):
                    writebyte(data[-disp])
            else:
                raise ValueError(flag)

            if decompressed_size <= len(data):
                break

    assert len(data) == decompressed_size

    #extra = f.read()
    #assert len(extra) == 0, repr(extra)

    return data

def main(args):
    f = open(args[0], "rb")

    # grab the underlying binary stream
    stdout = sys.stdout.detach()

    # the compression header is at the end of the file
    f.seek(-8, SEEK_END)
    header = f.read(8)

    # decompression goes backwards.
    # end < here < start

    # end_delta == here - decompression end address
    # start_delta == decompression start address - here
    end_delta, start_delta = unpack("<LL", header)

    filelen = f.tell()

    padding = end_delta >> 0x18
    end_delta &= 0xFFFFFF
    decompressed_size = start_delta + end_delta

    f.seek(filelen - end_delta, SEEK_SET)

    data = bytearray()
    data.extend(f.read(end_delta - padding))
    data.reverse()

    #stdout.write(data.tostring())

    uncompressed_data = decompress(data, decompressed_size)
    uncompressed_data.reverse()


    f.seek(0, SEEK_SET)
    # first we write up to the portion of the file which was "overwritten" by
    # the decompressed data, then the decompressed data itself.
    # i wonder if it's possible for decompression to overtake the compressed
    # data, so that the decompression code is reading its own output...
    try:
        stdout.write(f.read(filelen - end_delta))
        stdout.write(uncompressed_data)
    except IOError as e:
        if e.errno == EPIPE:
            # don't complain about a broken pipe
            pass
        else:
            raise

def main2(args):
    f = open(args[0], "rb")
    data = f.read()
    stdout = sys.stdout.detach()
    stdout.write(decompress(data))

if __name__ == '__main__':
    main(argv[1:])
    #main2(argv[1:])
