"""Find the Wii Party addresses the patches need in any release.

Everything is written once against the USA main.dol (SUPE01); the other releases share
the same compiled code at other addresses.  A function is located by matching
a window of USA instructions against the target DOL with the relocatable bits
(branch displacements, address halves, small-data offsets) masked out, and it
must match exactly once.  Data addresses are then read back from the matched
code (the lis/addi that references them), never guessed.
"""
import os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dol import Dol

def mask(w):
    op = w >> 26
    if op in (18,):                      # b / bl: keep opcode, AA, LK
        return w & 0xFC000003
    if op == 16:                         # bc: keep everything but displacement
        return w & 0xFFFF0003
    if op in (14, 15, 24, 25, 26, 27, 28, 29):   # addi/lis/ori/oris/xori/andi
        return w & 0xFFFF0000
    if 32 <= op <= 55:                   # loads/stores: drop displacement
        return w & 0xFFFF0000
    return w

def words(d, va, n):
    b = d.read(va, n * 4)
    return list(struct.unpack('>%dI' % n, b)) if b and len(b) == n * 4 else None

class Finder:
    def __init__(self, ref, tgt):
        self.ref, self.tgt = ref, tgt
        o, a, s, _ = [x for x in tgt.secs if x[3] == 1][0]
        self.tw = struct.unpack('>%dI' % (s // 4), tgt.data[o:o + s])
        self.tbase = a
        self.tm = [mask(w) for w in self.tw]

    def _hits(self, rm, tm, tbase, n):
        hits, first = [], rm[0]
        for i in range(len(tm) - n):
            if tm[i] == first and tm[i:i + n] == rm:
                hits.append(tbase + i * 4)
        return hits

    def locate(self, ref_va, n=24, ordered=False):
        """address in the target of the code at ref_va; must match exactly once, unless
        `ordered`: identical twins are then told apart by their order in the image"""
        rw = words(self.ref, ref_va, n)
        rm = [mask(w) for w in rw]
        hits = self._hits(rm, self.tm, self.tbase, n)
        if len(hits) != 1 and ordered:
            o, a, s, _ = [x for x in self.ref.secs if x[3] == 1][0]
            rtm = [mask(w) for w in struct.unpack('>%dI' % (s // 4), self.ref.data[o:o + s])]
            rhits = self._hits(rm, rtm, a, n)
            if len(rhits) == len(hits) and ref_va in rhits:
                return hits[rhits.index(ref_va)]
        if len(hits) != 1:
            raise SystemExit('anchor %08X: %d matches' % (ref_va, len(hits)))
        return hits[0]

    def pair(self, ref_va, ref_target, n=64):
        """the target revision's value for the address that the lis + addi pair
        near ref_va loads (ref_target on USA Rev 0)"""
        t_va = self.locate(ref_va)
        rw = words(self.ref, ref_va, n)
        tw = words(self.tgt, t_va, n)

        def imm(w):
            v = w & 0xFFFF
            return v - 0x10000 if v & 0x8000 else v

        for i in range(n):
            w = rw[i]
            if w >> 26 != 15:
                continue
            reg = (w >> 21) & 31
            for j in range(i + 1, min(n, i + 16)):
                w2 = rw[j]
                if w2 >> 26 == 14 and (w2 >> 16) & 31 == reg:
                    val = ((w & 0xFFFF) << 16) + imm(w2)
                    if val & 0xFFFFFFFF == ref_target:
                        t, t2 = tw[i], tw[j]
                        assert t >> 26 == 15 and t2 >> 26 == 14
                        return (((t & 0xFFFF) << 16) + imm(t2)) & 0xFFFFFFFF
        raise SystemExit('no pair for %08X near %08X' % (ref_target, ref_va))

import regions as R

# hook sites: located by the code that starts at the USA site
WINDOW = 24
FUNCS = {
    'SIGetType':   (0x801462F0, 40),
    'OSDisableInterrupts': (0x8013C030, 6),
    'OSRestoreInterrupts': (0x8013C070, 6),
}


def resolve(ref, tgt):
    """{site name: va} and the -D defines for `tgt`, a Dol of any release, against the USA `ref`."""
    f = Finder(ref, tgt)
    sites = {name: f.locate(va, WINDOW, ordered=True) for name, (va, _orig) in R.USA_SITES.items()}
    defs = {}
    fn = {k: f.locate(va, n) for k, (va, n) in FUNCS.items()}
    defs['FN_SIGETTYPE'] = fn['SIGetType']
    defs['FN_OSDISABLE'] = fn['OSDisableInterrupts']
    defs['FN_OSRESTORE'] = fn['OSRestoreInterrupts']
    defs['SI_TYPES'] = f.pair(0x801462F0, R.USA_DEFS['SI_TYPES'])
    defs['SI_BUSY'] = defs['SI_TYPES'] - 0x18
    defs['SI_SHADOW'] = defs['SI_BUSY'] + 4
    defs['WPAD_TBL'] = f.pair(0x8017C9E0, R.USA_DEFS['WPAD_TBL'])
    return sites, defs


if __name__ == '__main__':
    ref = Dol(sys.argv[1])
    for p in sys.argv[2:]:
        sites, defs = resolve(ref, Dol(p))
        print(os.path.basename(p))
        print('  sites', {k: '%08X' % v for k, v in sites.items()})
        print('  defs ', {k: '%08X' % v for k, v in defs.items()})
