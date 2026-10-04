"""Dolphin test lab: boot a disc (image or extracted dir) in a private user folder with the GDB stub on, feed
GameCube pad responses straight into the DEBUG_FEED build's state block, read KPAD state back, grab frames.

  from lab import Lab
  l = Lab('path/to/disc-dir-or-image'); l.start()
  l.pad(0, 'A'); l.wait(2); print(l.kpad(0)); l.shot('after_a.png'); l.stop()
"""
import glob, os, shutil, struct, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
from gdbmem import Gdb

DOLPHIN = '/Applications/Dolphin.app/Contents/MacOS/Dolphin'
PORT = 2477
STATE = 0x80001820
FEED = STATE + 0x10                 # struct st.feed[4][2] in the DEBUG_FEED build
KPAD0, KPAD_STRIDE = 0x802BC488, 0x688

BTN = dict(A=0x01000000, B=0x02000000, X=0x04000000, Y=0x08000000, S=0x10000000, Z=0x00100000, L=0x00400000,
           R=0x00200000, U=0x00080000, D=0x00040000, LT=0x00010000, RT=0x00020000)


def resp(*names):
    """GC pad response words for a set of held buttons / sticks:  'A', 'U', 'stk=0.5,-1', 'cst=0,1' ..."""
    h, l = 0x00808080, 0x80800000
    for name in names:
        if name in BTN:
            h |= BTN[name]
        elif name.startswith('stk='):
            x, y = [float(v) for v in name[4:].split(',')]
            h = (h & ~0xFFFF) | (int(128 + 127 * x) << 8) | int(128 + 127 * y)
        elif name.startswith('cst='):
            x, y = [float(v) for v in name[4:].split(',')]
            l = (int(128 + 127 * x) << 24) | (int(128 + 127 * y) << 16)
    return h, l


class Lab:
    def __init__(self, image, user=None, video='Metal', wiimote=None, frames=True, log=None):
        self.image = image
        self.user = os.path.abspath(user or os.path.join(HERE, 'user'))
        self.video, self.wiimote, self.frames = video, wiimote, frames
        self.log = log or os.path.join(self.user, 'dolphin.log')
        self.proc = None
        self.g = None
        self.running = False

    # ---- lifecycle -----------------------------------------------------------------------------
    def prepare(self):
        shutil.rmtree(self.user, ignore_errors=True)
        os.makedirs(os.path.join(self.user, 'Config'))
        ini = ("[General]\nGDBPort = %d\n[Interface]\nConfirmStop = False\nUsePanicHandlers = False\n"
               "[Core]\nMMU = True\nCPUThread = False\nCPUCore = 4\nEnableDebugging = True\nSIDevice0 = 0\n"
               "WiimoteContinuousScanning = False\nWiimoteControllerInterface = False\nOverrideRegionSettings = False\n"
               "[DSP]\nBackend = No Audio Output\n[Analytics]\nPermissionAsked = True\nEnabled = False\n" % PORT)
        if self.frames:
            ini += "[Movie]\nDumpFrames = True\nDumpFramesSilent = True\nDumpFramesAsImages = True\n"
        open(os.path.join(self.user, 'Config', 'Dolphin.ini'), 'w').write(ini)
        wm = ''
        for i in range(1, 5):
            src = 0
            if self.wiimote and i in self.wiimote:
                src = 1
            wm += '[Wiimote%d]\nSource = %d\n' % (i, src)
        open(os.path.join(self.user, 'Config', 'WiimoteNew.ini'), 'w').write(wm)

    def start(self, wait_gdb=True):
        self.prepare()
        self.out = open(self.log, 'w')
        self.proc = subprocess.Popen([DOLPHIN, '-b', '-u', self.user, '-e', self.image, '-v', self.video],
                                     stdout=self.out, stderr=subprocess.STDOUT)
        if wait_gdb:
            for _ in range(180):
                try:
                    self.g = Gdb(timeout=30)
                    break
                except OSError:
                    time.sleep(1)
            if self.g is None:
                raise RuntimeError('no GDB stub; see ' + self.log)
            self.g.cont()
            self.running = True
        self.t0 = time.time()

    def stop(self):
        if self.g:
            self.g.close()
        if self.proc:
            self.proc.terminate()
            try:
                self.proc.wait(10)
            except Exception:
                self.proc.kill()

    def wait(self, secs):
        time.sleep(secs)

    # ---- memory --------------------------------------------------------------------------------
    def _halt(self):
        if self.running:
            self.g.interrupt()
            self.running = False

    def _go(self):
        if not self.running:
            self.g.cont()
            self.running = True

    def read(self, addr, n):
        self._halt()
        try:
            return self.g.read_mem(addr, n)
        finally:
            self._go()

    def write(self, addr, data):
        self._halt()
        try:
            self.g.cmd('M%x,%x:%s' % (addr, len(data), data.hex()))
        finally:
            self._go()

    def pad(self, chan, *names):
        """hold these buttons on GC port chan+1 (no names: neutral pad present; 'off': unplugged)"""
        if names == ('off',):
            h, l = 0, 0
        else:
            h, l = resp(*names)
        self.write(FEED + chan * 8, struct.pack('>II', h, l))

    def kpad(self, chan):
        k = KPAD0 + chan * KPAD_STRIDE
        b = self.read(k, 0x80)
        hold, trig, rel = struct.unpack('>III', b[0:12])
        acc = struct.unpack('>fff', b[0xC:0x18])
        stk = struct.unpack('>ff', b[0x6C:0x74])
        return dict(hold=hold, trig=trig, rel=rel, acc=acc, stick=stk, dev=b[0x5C], err=b[0x5D], fmt=b[0x5F],
                    scheme=struct.unpack('>I', self.read(STATE, 4))[0])

    # ---- frames --------------------------------------------------------------------------------
    def frames_dir(self):
        return os.path.join(self.user, 'Dump', 'Frames')

    def latest_frame(self):
        fr = sorted(glob.glob(os.path.join(self.frames_dir(), '**', '*.png'), recursive=True), key=os.path.getmtime)
        return fr[-1] if fr else None

    def shot(self, dest, settle=0.5):
        time.sleep(settle)
        f = self.latest_frame()
        if f:
            time.sleep(0.2)
            shutil.copy(f, dest)
        return dest if f else None


def tap(l, chan, *names, hold=0.3, gap=1.0):
    l.pad(chan, *names)
    time.sleep(hold)
    l.pad(chan)
    time.sleep(gap)
