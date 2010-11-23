# used http://code.google.com/p/u-lzss/source/browse/trunk/js/lib/ulzss.js as
# a guide
from sys import stderr

from operator import itemgetter
from struct import pack, unpack


class SlidingWindow:
    def __init__(self, size, type=bytearray, match_min=1, match_max=None):
        if match_max is None:
            match_max = size
        self.size = size
        self.data = type()
        self.full = False
        self.nextindex = 0
        self.match_max = min(size, match_max)
        self.match_min = match_min

    def append(self, item):
        if self.full:
            self.data[self.nextindex] = item
            self.nextindex = (self.nextindex + 1) % self.size
        else:
            self.data.append(item)
            self.nextindex += 1
            if self.size <= self.nextindex:
                self.full = True
                self.nextindex = 0

    def extend(self, items):
        for x in items:
            self.append(x)

    def search(self, buf):
        """ pathologically stupid search function """
        counts = []
        start = self.nextindex if self.full else 0
        size = self.size if self.full else self.nextindex
        match_max = min(self.match_max, size)
        match_min = self.match_min

        for i in range(size):
            matchlen = self.match(buf, start + i)
            if matchlen >= match_min:
                counts.append((matchlen, i - size))
                if matchlen >= match_max:
                    return counts[-1]

        if counts:
            match = max(counts, key=itemgetter(0))
            return match

        return None

    def match(self, buf, i):
        matchlen = 0
        if self.full:
            size = self.size - i
        else:
            size = self.nextindex - i

        if size == 0:
            return 0

        matchlen = 0
        for n in range(min(len(buf), self.match_max)):
            if buf[n] == self.data[(i + (n % size)) % self.size]:
                matchlen += 1
            else:
                break
        return matchlen

#class LZWindow:
#    
#    size = 2 ** 12
#
#    def __init__(self, ):
#        
#    
#    def search(self):
#        
#


def _compress(input):
    """Generates a stream of tokens. Either a byte (int) or a tuple of (count,
    displacement)."""

    window = SlidingWindow(size=2**12, match_min=3, match_max=3+15)
    #window = SlidingWindow(size=2**12, match_min=3, match_max=0x111+0xffff)

    i = 0
    while True:
        if len(input) <= i:
            break
        match = window.search(input[i:])
        if match:
            yield match
            i2 = i + match[0]
        else:
            yield input[i]
            i2 = i + 1

        window.extend(input[i:i2])
        i = i2

def packflags(flags):
    n = 0
    for i in range(8):
        n <<= 1
        try:
            if flags[i]:
                n |= 1
        except IndexError:
            pass
    return n

def chunkit(it, n):
    buf = []
    for x in it:
        buf.append(x)
        if n <= len(buf):
            yield buf
            buf = []
    if buf:
        yield buf

def compress(input, out):
    # header
    out.write(pack("<L", (len(input) << 8) + 0x10))

    # body
    length = 0
    for tokens in chunkit(_compress(input), 8):
        flags = [type(t) == tuple for t in tokens]
        out.write(pack(">B", packflags(flags)))

        for t in tokens:
            if type(t) == tuple:
                count, disp = t
                count -= 3
                disp = (-disp) - 1
                sh = (count << 12) | disp
                #print (sh, file=stderr)
                out.write(pack(">H", sh))
            else:
                out.write(pack(">B", t))

        length += 1
        length += sum(2 if f else 1 for f in flags)

    # padding
    padding = 4 - (length % 4 or 4)
    if padding:
        out.write(b'\xff' * padding)


if __name__ == '__main__':
    from sys import stdout, argv
    data = open(argv[1], "rb").read()
    stdout = stdout.detach()
    compress(data, stdout)
