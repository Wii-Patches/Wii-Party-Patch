#!/usr/bin/env python3
"""Keep one Dolphin running and take commands on localhost:2478, one per line (ctl.py is the client).

  labd.py <image> [feed]        feed: the image is a DEBUG_FEED build (pads driven through the debugger)

  pad <chan> [names..|off]      hold these pad buttons         tap <chan> <names..> [hold] [gap]
  seq <chan> a,b,c..            tap each, one second apart     kpad <chan>            KPAD state of a channel
  shot <file>                   latest frame -> file           read <hexaddr> <n>     memory
  write <hexaddr> <hexbytes>    poke memory                    quit
"""
import json, socketserver, sys, time
sys.path.insert(0, __file__.rsplit('/', 1)[0])
sys.path.insert(0, __file__.rsplit('/', 1)[0] + '/../tools')
from lab import *

lab = None
import threading
LOCK = threading.Lock()


class H(socketserver.StreamRequestHandler):
    def handle(self):
        for raw in self.rfile:
            a = raw.decode().split()
            if not a:
                continue
            try:
                with LOCK:
                    out = run(a)
            except Exception as e:
                out = 'ERR %s' % e
            self.wfile.write((json.dumps(out) if not isinstance(out, str) else out).encode() + b'\n')
            if a[0] == 'quit':
                return


def run(a):
    c = a[0]
    if c == 'pad':
        lab.pad(int(a[1]), *a[2:]); return 'ok'
    if c == 'tap':
        names = [x for x in a[2:] if not x.startswith(('hold=', 'gap='))]
        kw = dict(x.split('=') for x in a[2:] if x.startswith(('hold=', 'gap=')))
        tap(lab, int(a[1]), *names, hold=float(kw.get('hold', 0.3)), gap=float(kw.get('gap', 1.0))); return 'ok'
    if c == 'seq':
        for s in a[2].split(','):
            tap(lab, int(a[1]), *s.split('+'), hold=0.3, gap=1.0)
        return 'ok'
    if c == 'kpad':
        return lab.kpad(int(a[1]))
    if c == 'shot':
        return lab.shot(a[1]) or 'noframe'
    if c == 'read':
        return lab.read(int(a[1], 16), int(a[2])).hex()
    if c == 'write':
        lab.write(int(a[1], 16), bytes.fromhex(a[2])); return 'ok'
    if c == 'reload':
        import patcher, struct as st
        data = patcher.load('SUPE01', True)
        blob, placed = patcher.layout(data, [s for f in patcher.ORDER for s in data['features'][f]])
        sz = 0
        lab._halt()
        try:
            for off in range(sz, len(blob), 512):
                chunk = bytes(blob[off:min(off + 512, len(blob))])
                lab.g.cmd('M%x,%x:%s' % (patcher.LOW + off, len(chunk), chunk.hex()))
            for va, at in placed:
                lab.g.cmd('M%x,4:%s' % (va, st.pack('>I', patcher.branch(va, at)).hex()))
        finally:
            lab._go()
        return 'reloaded %d bytes' % (len(blob) - sz)
    if c == 'quit':
        lab.stop(); __import__('os')._exit(0)
    return 'unknown'


if __name__ == '__main__':
    lab = Lab(sys.argv[1], video=__import__('os').environ.get('VIDEO', 'Metal'),
              wiimote=[int(x) for x in __import__('os').environ.get('WM', '').split(',') if x])
    lab.start()
    print('ready', flush=True)
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer(('127.0.0.1', 2478), H) as s:
        s.serve_forever()
