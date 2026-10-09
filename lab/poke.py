"""poke.py <off=value-float>... | off	  -- fill the debug poke table (feed builds): the hook writes these floats
into player 1's KPAD struct every sample, the sign flipping each frame.   poke.py off  clears it"""
import struct, subprocess, sys
BASE = 0x80005E78 + 0x1BC


def w(addr, words):
    subprocess.run(['python3', 'ctl.py', 'write', '%x' % addr, b''.join(struct.pack('>I', x) for x in words).hex()],
                   check=True, stdout=subprocess.DEVNULL)


if sys.argv[1] == 'off':
    w(BASE, [0])
else:
    pairs = []
    for a in sys.argv[1:]:
        off, v = a.split('=')
        pairs += [int(off, 16), struct.unpack('>I', struct.pack('>f', float(v)))[0]]
    w(BASE + 4, pairs + [0, 0])
    w(BASE, [1])
