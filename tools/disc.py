"""Patch a whole Wii Party disc image: extract with wit, patch sys/main.dol, rebuild.

The rebuilt image replaces the original in place, keeping its filename and
folder (USB loaders key off the `/wbfs/<Title> [ID6]/` layout); the untouched
original is kept next to it as `<name>.bak`.
"""
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import patcher
from dol import Dol
from regions import REGIONS, region_of_disc


def find_wit():
    """A wit bundled with this app (PyInstaller build) wins over PATH.

    --add-binary'd files land next to sys._MEIPASS: a plain onedir build puts
    them in _internal/, and a windowed macOS .app puts them in
    Contents/Frameworks/ instead of Contents/MacOS/ alongside the binary.
    """
    name = 'wit.exe' if os.name == 'nt' else 'wit'
    if getattr(sys, 'frozen', False):
        for base in (getattr(sys, '_MEIPASS', None), os.path.dirname(sys.executable)):
            if base:
                bundled = os.path.join(base, name)
                if os.path.isfile(bundled):
                    return bundled
    return shutil.which('wit')


def find_file(root, name):
    for r, _, files in os.walk(root):
        if name in files:
            return os.path.join(r, name)
    return None


def read_disc_id(fst):
    boot = find_file(fst, 'boot.bin')
    if not boot:
        return None
    with open(boot, 'rb') as f:
        header = f.read(8)
    return header[0:6].decode('ascii', 'replace'), header[7]


def run_patch(image_path, log, done, which=('cc', 'gc')):
    """Patch `image_path` in place.  `which` names the features (see patcher.FEATURES)."""
    try:
        wit = find_wit()
        if wit is None:
            raise RuntimeError('wit (Wiimms ISO Tool) not found: not bundled with this '
                               'build and not on PATH')
        which = [w for w in patcher.ORDER if w in which]
        if not which:
            raise RuntimeError('nothing selected: tick at least one patch')
        fmt = '--iso' if image_path.lower().endswith('.iso') else '--wbfs'

        with tempfile.TemporaryDirectory(prefix='wiiparty_patch_') as tmp:
            fst = os.path.join(tmp, 'fst')
            log('extracting %s...' % os.path.basename(image_path))
            r = subprocess.run([wit, 'extract', image_path, '--dest', fst, '--psel', 'data',
                                '--overwrite', '-q'], capture_output=True, text=True)
            if r.returncode:
                raise RuntimeError('extract failed:\n' + (r.stderr or r.stdout))

            got = read_disc_id(fst)
            if not got:
                raise RuntimeError('could not read sys/boot.bin from the extracted disc')
            disc_id, disc_ver = got
            region = region_of_disc(disc_id, disc_ver)
            if region is None:
                raise RuntimeError('%s v%d is not a Wii Party release this patcher knows.\n\nSupported: %s' % (
                    disc_id, disc_ver, ', '.join('%s (%s)' % (i, v['short']) for i, v in sorted(
                        ((d[0], r) for r in REGIONS.values() for d in r['discs']), key=lambda x: x[0]))))
            log('disc: %s (%s)' % (disc_id, REGIONS[region]['label']))

            dol_path = find_file(fst, 'main.dol')
            if not dol_path or os.path.basename(os.path.dirname(dol_path)) != 'sys':
                raise RuntimeError('could not find sys/main.dol in the extracted disc')
            dol = Dol(dol_path)

            have = patcher.status(dol, region)
            for name in which:
                if have.get(name) == 'patched':
                    raise RuntimeError('this disc already has a patch in it. Patch a clean copy instead '
                                       '(the original is kept as <name>.bak next to a patched one).')
                if have.get(name) != 'clean':
                    raise RuntimeError('the main.dol does not match the retail %s release -- already modified '
                                       'by something else, or not an unmodified dump. Not patching it.'
                                       % REGIONS[region]['label'])
            for t in patcher.patch(dol, region, which):
                log('  added %s' % t)
            dol.save(dol_path)
            log('  patched main.dol')

            staged = os.path.join(tmp, 'patched.img')
            log('rebuilding...')
            cmd = [wit, 'copy', fst, '--dest', staged, fmt, '--overwrite', '-q']
            r = subprocess.run(cmd, capture_output=True, text=True)
            if r.returncode:
                raise RuntimeError('rebuild failed:\n' + (r.stderr or r.stdout))

            # Only touch the user's file once the rebuild has actually succeeded.
            backup = image_path + '.bak'
            if os.path.exists(backup):
                log('  backup already exists, keeping it: %s' % os.path.basename(backup))
            else:
                shutil.copyfile(image_path, backup)
                log('  backed up original -> %s' % os.path.basename(backup))
            shutil.move(staged, image_path)
            log('done: patched in place, %s' % os.path.basename(image_path))
            done(True, image_path)
    except Exception as e:
        log('ERROR: %s' % e)
        done(False, str(e))
