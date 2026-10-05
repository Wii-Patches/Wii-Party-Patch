#!/usr/bin/env python3
"""Command-line twin of the GUI: patch a .wbfs/.iso in place.

    python3 tools/patch_disc.py "Wii Party (USA).wbfs" --cc --gc
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import disc
import patcher


def main():
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    ap.add_argument('image')
    for n in patcher.ORDER:
        ap.add_argument('--' + n, action='store_true', help=patcher.FEATURES[n])
    a = ap.parse_args()
    which = [n for n in patcher.ORDER if getattr(a, n)] or list(patcher.ORDER)
    ok = []
    disc.run_patch(a.image, print, lambda good, msg: ok.append(good), which)
    sys.exit(0 if ok and ok[0] else 1)


if __name__ == '__main__':
    main()
