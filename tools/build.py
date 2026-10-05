#!/usr/bin/env python3
"""Dev-time: compile src/ into tools/prebuilt/<release>.json.

  python3 tools/build.py [--dols DIR] [--debug-feed]

Needs devkitPPC and, for every release but USA, your own main.dol dumps (SUPE01.dol, SUPJ01.dol, SUPJ01v1.dol,
SUPK01.dol in DIR, or $WIIPARTY_DOLS): the other releases' addresses are found from them (tools/anchors.py).  End users never run this -- the patcher reads the prebuilt
JSON, which holds only this project's code (never anything from the game).
The JSON for one release is

  {"state": va, "state_size": n,
   "features": {"cc": [site, ...], "gc": [site, ...]}}   site = {"name", "va", "orig", "words"}

`words` is a hook body; its last word is a placeholder the installer turns
into the branch back to va+4.  `orig` is the retail word expected at the site.
"""
import json, os, struct, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import asm
import regions as R

DEVKIT = os.environ.get('DEVKITPPC', '/opt/devkitpro/devkitPPC')
CC = DEVKIT + '/bin/powerpc-eabi-'
FEATURES = {'cc': ['cc_buttons', 'cc_stick', 'cc_tilt', 'cc_ptr1', 'cc_ptr2'], 'gc': ['gc_poll', 'gc_sample', 'gc_probe']}

# Wii Party's Classic Controller stick values: see docs/TECHNICAL.md
STICK_SCALE, STICK_MAX, CSTICK_MAX = 3, 308, 361
PTR_SPEED_X, PTR_SPEED_Y = 0x3FCCCCCD, 0x3F99999A      # floats: 1.6 and 1.2 screens per second at full stick
C_HOOKS = ('gc_poll', 'gc_sample', 'gc_probe', 'cc_ptr1', 'cc_ptr2')


def compile_gc(hook, defs, debug=False):
    src = os.path.join(ROOT, 'src')
    tmp = tempfile.mkdtemp(prefix='wpgc')
    D = ['-D%s=0x%08Xu' % kv for kv in defs.items()]
    D += ['-DSTATE=0x%08Xu' % R.STATE, '-DHOOK_' + hook.split('_')[1].upper(),
          '-DSTICK_SCALE=%d' % STICK_SCALE, '-DSTICK_MAX=%d' % STICK_MAX,
          '-DCSTICK_MAX=%d' % CSTICK_MAX, '-DPTR_SPEED_X=0x%08Xu' % PTR_SPEED_X, '-DPTR_SPEED_Y=0x%08Xu' % PTR_SPEED_Y]
    if debug:
        D.append('-DDEBUG_FEED')
    fp = '-mhard-float' if hook.startswith('cc_ptr') else '-msoft-float'
    cflags = ['-O2', '-fno-unroll-loops', '-mbig-endian', fp, '-mcpu=750', '-msdata=none', '-ffreestanding',
              '-fno-pic', '-fno-asynchronous-unwind-tables', '-fno-stack-protector', '-nostdlib', '-Wall']
    subprocess.check_call([CC + 'gcc'] + cflags + D + ['-c', src + '/gcpad.c', '-o', tmp + '/g.o'])
    subprocess.check_call([CC + 'gcc', '-mbig-endian', '-c', '-x', 'assembler-with-cpp'] + D +
                          [src + '/hooks.S', '-o', tmp + '/h.o'])
    subprocess.check_call([CC + 'ld', '-T', src + '/link.ld', '-o', tmp + '/b.elf', tmp + '/h.o', tmp + '/g.o'])
    subprocess.check_call([CC + 'objcopy', '-O', 'binary', tmp + '/b.elf', tmp + '/b.bin'])
    return asm.words(open(tmp + '/b.bin', 'rb').read())


def assemble_cc(hook):
    text = open(os.path.join(ROOT, 'src', hook + '.s')).read()
    return asm.words(asm.assemble(text, 0, consts={'STATE': R.STATE}))


def resolve(region, dols):
    """({hook: (va, retail word)}, defines) for a release."""
    if R.REGIONS[region].get('reference'):
        return R.USA_SITES, R.USA_DEFS
    import anchors
    from dol import Dol
    ref = Dol(os.path.join(dols, R.REGIONS['SUPE01']['dol']))
    tgt = Dol(os.path.join(dols, R.REGIONS[region]['dol']))
    found, defs = anchors.resolve(ref, tgt)
    sites = {}
    for name, va in found.items():
        w = struct.unpack('>I', tgt.read(va, 4))[0]
        usa_w = R.USA_SITES[name][1]
        # the anchors match with address halves and displacements masked: the displaced word may differ there only
        assert anchors.mask(w) == anchors.mask(usa_w), '%s %s: %08X is not the expected instruction' % (region, name, w)
        sites[name] = (va, w)
    return sites, defs


def build(region, dols, debug=False):
    sites, defs = resolve(region, dols)
    out = {'state': R.STATE, 'state_size': R.STATE_SIZE, 'features': {}}
    for feat, hooks in FEATURES.items():
        out['features'][feat] = []
        for h in hooks:
            va, orig = sites[h]
            words = compile_gc(h, defs, debug) if h in C_HOOKS else assemble_cc(h)
            assert words[-1] == 0x60000000, '%s must end with a nop slot' % h
            if len(words) % 2:
                words.insert(len(words) - 1, 0x60000000)
            out['features'][feat].append({'name': h, 'va': va, 'orig': orig, 'words': words})
    return out


def main():
    debug = '--debug-feed' in sys.argv
    dols = os.environ.get('WIIPARTY_DOLS', 'dols')
    if '--dols' in sys.argv:
        dols = sys.argv[sys.argv.index('--dols') + 1]
    outdir = os.path.join(HERE, 'prebuilt')
    os.makedirs(outdir, exist_ok=True)
    for region in R.REGIONS:
        data = build(region, dols, debug)
        name = region + ('_feed' if debug else '') + '.json'
        json.dump(data, open(os.path.join(outdir, name), 'w'), indent=1)
        print(name, {s['name']: len(s['words']) * 4 for f in data['features'].values() for s in f})


if __name__ == '__main__':
    main()
