#!/usr/bin/env python3
"""Dev-time: compile src/ into tools/prebuilt/<disc id>.json.

  python3 tools/build.py [--debug-feed]

Needs devkitPPC.  End users never run this -- the patcher reads the prebuilt
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
FEATURES = {'cc': ['cc_buttons', 'cc_stick', 'cc_tilt'], 'gc': ['gc_poll', 'gc_sample', 'gc_probe']}

# Wii Party's Classic Controller stick values: see docs/TECHNICAL.md
STICK_SCALE, STICK_MAX = 3, 308


def compile_gc(hook, defs, debug=False):
    src = os.path.join(ROOT, 'src')
    tmp = tempfile.mkdtemp(prefix='wpgc')
    D = ['-D%s=0x%08Xu' % kv for kv in defs.items()]
    D += ['-DSTATE=0x%08Xu' % R.STATE, '-DHOOK_' + hook.split('_')[1].upper(),
          '-DSTICK_SCALE=%d' % STICK_SCALE, '-DSTICK_MAX=%d' % STICK_MAX]
    if debug:
        D.append('-DDEBUG_FEED')
    cflags = ['-O2', '-fno-unroll-loops', '-mbig-endian', '-msoft-float', '-msdata=none', '-ffreestanding',
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


def build(region, debug=False):
    sites, defs = R.USA_SITES, R.USA_DEFS
    out = {'state': R.STATE, 'state_size': R.STATE_SIZE, 'features': {}}
    for feat, hooks in FEATURES.items():
        out['features'][feat] = []
        for h in hooks:
            va, orig = sites[h]
            words = compile_gc(h, defs, debug) if h.startswith('gc_') else assemble_cc(h)
            assert words[-1] == 0x60000000, '%s must end with a nop slot' % h
            if len(words) % 2:
                words.insert(len(words) - 1, 0x60000000)
            out['features'][feat].append({'name': h, 'va': va, 'orig': orig, 'words': words})
    return out


def main():
    debug = '--debug-feed' in sys.argv
    outdir = os.path.join(HERE, 'prebuilt')
    os.makedirs(outdir, exist_ok=True)
    for region in R.REGIONS:
        data = build(region, debug)
        name = region + ('_feed' if debug else '') + '.json'
        json.dump(data, open(os.path.join(outdir, name), 'w'), indent=1)
        print(name, {s['name']: len(s['words']) * 4 for f in data['features'].values() for s in f})


if __name__ == '__main__':
    main()
