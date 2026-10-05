#!/usr/bin/env python3
"""Consistency checks that need no game files (CI runs this).

Every prebuilt release loads, its hook bodies fit below the patch limit, and
every hook body is non-empty.

    python3 tools/check.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import patcher
from regions import REGIONS

fail = []


def check(cond, msg):
    if not cond:
        fail.append(msg)
        print('  FAIL', msg)


for region in REGIONS:
    try:
        data = patcher.load(region)
    except FileNotFoundError:
        check(False, 'missing prebuilt/%s.json' % region)
        continue
    check(set(data['features']) == set(patcher.ORDER), '%s: features %s' % (region, sorted(data['features'])))
    sites = [s for f in data['features'].values() for s in f]
    try:
        patcher.layout(data, sites)
    except ValueError as e:
        check(False, '%s: %s' % (region, e))
    for s in sites:
        check(s['words'] and all(isinstance(w, int) for w in s['words']), '%s/%s: empty hook body' % (region, s['name']))

print('FAILED: %d' % len(fail) if fail else 'ok: all checks passed')
sys.exit(1 if fail else 0)
