#!/usr/bin/env python2

from sys import argv, stdout
from os import SEEK_END, SEEK_CUR, SEEK_SET
from struct import pack, unpack
from array import array
from cStringIO import StringIO

def bits(byte):
    return ((byte >> 7) & 1,
            (byte >> 6) & 1,
            (byte >> 5) & 1,
            (byte >> 4) & 1,
            (byte >> 3) & 1,
            (byte >> 2) & 1,
            (byte >> 1) & 1,
            (byte) & 1)

def decompress(f):
    """Decompress an LZSS-compressed file. Returns an array.array."""
    data = array('c')

    def write(s):
        data.extend(s)
    def readbyte():
        return unpack(">B", f.read(1))[0]
    def readshort():
        return unpack(">H", f.read(2))[0]

    b = readbyte()
    assert b == 0x10
    decompressed_size, = unpack("<L", f.read(3) + "\x00")
    #print hex(decompressed_size)

    while len(data) < decompressed_size:
        b = readbyte()
        if b == '\x00':
            # optimization
            write(f.read(8))
            continue
        flags = bits(b)
        for flag in flags:
            if flag == 0:
                write(f.read(1))
            elif flag == 1:
                sh = readshort()
                count = (sh >> 0xc) + 3
                disp = (sh & 0xfff) + 3

                for _ in range(count):
                    write(data[-disp])
            else:
                raise ValueError(flag)

            if decompressed_size <= len(data):
                break

    assert len(data) == decompressed_size

    #extra = f.read()
    #assert len(extra) == 0, repr(extra)

    return data

def main():
    f = open(argv[1], "rb")
    f.seek(-8, SEEK_END)
    header = f.read(8)

    # end_offset == here - end of decompression
    # start_offset == start of decompression - here
    # end < here < start
    end_offset, start_offset = unpack("<LL", header)

    armlen = f.tell()

    padding = end_offset >> 0x18
    end_offset &= 0xFFFFFF
    uncompressed_size = start_offset + end_offset

    start_offset -= padding

    f.seek(0, SEEK_SET)

    header = '\x10' + pack("<L", uncompressed_size)[:3]
    data = array('c')
    data.fromfile(f, armlen - padding)
    data.extend(header[::-1])
    data.reverse()

    #stdout.write(data.tostring())

    infile = StringIO(data.tostring())
    uncompressed_data = decompress(infile)
    uncompressed_data.reverse()

    f.seek(0, SEEK_SET)
    stdout.write(f.read(armlen - end_offset))
    uncompressed_data.tofile(stdout)

if __name__ == '__main__':
    main()
