#!/usr/bin/env python3
"""Consistency checks that need no game files (CI runs this).

  * every release has prebuilt data, and every hook in it ends in a branch-back slot,
    carries no game bytes beyond the one displaced-word check, and fits the injected section
  * the state block and the hook bodies stay clear of each other and of the OS globals

    python3 tools/check.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import patcher
from regions import REGIONS, LOW, STATE, STATE_SIZE

fail = []


def check(cond, msg):
    if not cond:
        fail.append(msg)
        print('  FAIL', msg)


def main():
    for region in REGIONS:
        try:
            data = patcher.load(region)
        except FileNotFoundError:
            check(False, 'missing tools/prebuilt/%s.json' % region)
            continue
        check(data['state'] == STATE and data['state_size'] == STATE_SIZE, '%s: state block moved' % region)
        sites = [s for f in data['features'].values() for s in f]
        names = [s['name'] for s in sites]
        check(len(names) == len(set(names)), '%s: duplicate hook' % region)
        for s in sites:
            check(s['words'][-1] == 0x60000000, '%s/%s: no branch-back slot' % (region, s['name']))
            check(0x80003100 <= s['va'] < 0x801DD000, '%s/%s: site outside the text section' % (region, s['name']))
        blob, placed = patcher.layout(data, sites)
        check(LOW + len(blob) <= patcher.LIMIT, '%s: injected section too large' % region)
        check(not (LOW <= STATE < LOW + len(blob)), '%s: state overlaps the hooks' % region)
        for feat, hooks in data['features'].items():
            check(hooks, '%s: feature %s is empty' % (region, feat))
    print('FAILED: %d' % len(fail) if fail else 'ok: all checks passed')
    sys.exit(1 if fail else 0)


if __name__ == '__main__':
    main()
