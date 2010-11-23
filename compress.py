# used http://code.google.com/p/u-lzss/source/browse/trunk/js/lib/ulzss.js as
# a guide
from sys import stderr

from collections import defaultdict
from operator import itemgetter
from struct import pack, unpack

class SlidingWindow:
    def __init__(self, buf, size=4096, disp_min=1, match_min=1, match_max=None):
        self.data = buf
        self.hash = defaultdict(list)
        self.full = False

        self.size = size
        self.start = 0
        self.stop = 0
        self.index = disp_min - 1

        self.match_min = match_min

        if match_max is None:
            match_max = size
        self.match_max = min(size, match_max)

        self.disp_min = disp_min

    def next(self):
        if self.full:
            olditem = self.data[self.start]
            self.hash[olditem].pop(0)

        item = self.data[self.stop]
        self.hash[item].append(self.stop)
        self.stop += 1
        self.index += 1

        if self.full:
            self.start += 1
        else:
            if self.size <= self.stop:
                self.full = True

    def advance(self, n=1):
        """Advance the window by n bytes"""
        for _ in range(n):
            self.next()

    def search(self):
        start = self.start
        stop = self.stop
        size = self.size if self.full else self.stop

        match_max = min(self.match_max, size)
        match_min = self.match_min

        counts = []
        indices = self.hash[self.data[self.index]]
        for i in indices:
            matchlen = self.match(i, self.index)
            if matchlen >= match_min:
                disp = self.index - i
                counts.append((matchlen, -disp))
                if matchlen >= match_max:
                    return counts[-1]

        if counts:
            match = max(counts, key=itemgetter(0))
            return match

        return None

    def match(self, start, bufstart):
        size = self.index - start

        if size == 0:
            return 0

        matchlen = 0
        it = range(min(len(self.data) - bufstart, self.match_max))
        for i in it:
            if self.data[start + (i % size)] == self.data[bufstart + i]:
                matchlen += 1
            else:
                break
        return matchlen

def _compress(input):
    """Generates a stream of tokens. Either a byte (int) or a tuple of (count,
    displacement)."""

    window = SlidingWindow(input, size=2**12, match_min=3, match_max=3+15)
    #window = SlidingWindow(input, size=2**12, match_min=3, match_max=0x111+0xffff)

    i = 0
    while True:
        if len(input) <= i:
            break
        match = window.search()
        if match:
            yield match
            window.advance(match[0])
            i += match[0]
        else:
            yield input[i]
            window.next()
            i += 1

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
                assert 0 <= disp < 4096
                sh = (count << 12) | disp
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
