"""Apply the selected patches to one Wii Party main.dol.

The hook bodies and the shared state block go in one new text section at
0x80001820 (the Wii's boot-time scratch area, which this game never touches;
a USB loader's code handler lives at 0x80001800, so turn its cheats off).  Each
hook site becomes a branch to its body, and the last word of every body
branches back to site+4.
"""
import json, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from dol import Dol
from regions import REGIONS, LOW

LIMIT = 0x80003000
FEATURES = {
    'cc': 'Classic Controller support',
    'gc': 'GameCube controller support (ports 1-4)',
}
ORDER = ('cc', 'gc')


def load(region, feed=False):
    return json.load(open(os.path.join(HERE, 'prebuilt', region + ('_feed' if feed else '') + '.json')))


def branch(frm, to):
    off = to - frm
    assert off % 4 == 0 and -0x2000000 <= off < 0x2000000
    return 0x48000000 | (off & 0x03FFFFFC)


def word(dol, va):
    b = dol.read(va, 4)
    return struct.unpack('>I', b)[0] if b else None


def detect_region(dol):
    """Which release this main.dol is (None if unknown), by its retail hook sites."""
    for region in REGIONS:
        try:
            data = load(region)
        except FileNotFoundError:
            continue
        sites = [s for f in data['features'].values() for s in f]
        if all(word(dol, s['va']) in (s['orig'], None) or is_patched(dol, s) for s in sites) \
                and any(word(dol, s['va']) == s['orig'] or is_patched(dol, s) for s in sites):
            return region
    return None


def is_patched(dol, site):
    w = word(dol, site['va'])
    return w is not None and w >> 26 == 18 and w & 3 == 0 and \
        LOW <= (site['va'] + (((w & 0x03FFFFFC) ^ 0x02000000) - 0x02000000)) < LIMIT


def status(dol, region, feed=False):
    """{feature: 'clean' | 'patched' | 'mismatch'}"""
    data = load(region, feed)
    out = {}
    for feat, sites in data['features'].items():
        states = ['patched' if is_patched(dol, s) else 'clean' if word(dol, s['va']) == s['orig'] else 'mismatch'
                  for s in sites]
        out[feat] = states[0] if len(set(states)) == 1 else 'mismatch'
    return out


def patch(dol, region, which, feed=False):
    """Patch `dol` (a dol.Dol) in place; returns the titles applied."""
    data = load(region, feed)
    st = status(dol, region, feed)
    which = [f for f in ORDER if f in which]
    if not which:
        raise ValueError('nothing selected')
    if 'gc' in which and 'cc' not in which and st['cc'] != 'patched':
        which.insert(0, 'cc')       # the pad is presented to the game as a Classic Controller
    for f in which:
        if st[f] != 'clean':
            raise ValueError('%s: this main.dol is %s' % (FEATURES[f], 'already patched' if st[f] == 'patched'
                                                           else 'not the retail one'))
    # the section is created once; a second run adds hooks into the existing one
    existing = any(a == LOW and s for a, s in zip(dol.addr, dol.size))
    sites = [s for f in which for s in data['features'][f]]
    if existing:
        raise ValueError('this main.dol already carries a patch section; patch a clean one with every feature '
                         'selected at once')
    blob = bytearray(data['state_size'])
    placed = []
    for s in sites:
        at = LOW + len(blob)
        w = list(s['words'])
        w[-1] = branch(at + 4 * (len(w) - 1), s['va'] + 4)
        blob += struct.pack('>%dI' % len(w), *w)
        placed.append((s['va'], at))
    if LOW + len(blob) > LIMIT:
        raise ValueError('patch does not fit below 0x%08X' % LIMIT)
    dol.add_text_section(LOW, bytes(blob))
    for va, at in placed:
        dol.write(va, struct.pack('>I', branch(va, at)))
    return [FEATURES[f] for f in which]


def patch_file(src, dst, region, which, feed=False):
    dol = Dol(src)
    done = patch(dol, region, which, feed)
    dol.save(dst)
    return done


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description='Patch a Wii Party main.dol')
    ap.add_argument('src')
    ap.add_argument('dst')
    ap.add_argument('--region', choices=sorted(REGIONS), help='default: detect')
    ap.add_argument('--feed', action='store_true', help='debug build: pad responses fed by a debugger')
    for n in ORDER:
        ap.add_argument('--' + n, action='store_true', help=FEATURES[n])
    a = ap.parse_args()
    d = Dol(a.src)
    reg = a.region or detect_region(d)
    if not reg:
        sys.exit('could not identify this main.dol; pass --region')
    which = [n for n in ORDER if getattr(a, n)] or list(ORDER)
    print(reg, REGIONS[reg]['label'], '->', ', '.join(patch_file(a.src, a.dst, reg, which, a.feed)))
