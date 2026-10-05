/* GameCube controllers (ports 1-4) -> Classic Controller bridge for Wii Party.
 *
 * Three hooks, one blob each (see hooks.S for the register-saving entry
 * stubs).  The game links the SI library but not PAD, so nothing ever polls
 * the pads: gc_poll() drives the Serial Interface's own auto-polling.
 * gc_sample() turns a pad's state into a Classic Controller sample in KPAD's
 * ring, and gc_probe() makes WPADProbe report a Classic Controller on the
 * channel, so the game, and the Classic Controller hooks in cc_*.s, treat a
 * GameCube pad as one.  Port N drives player N.
 *
 * Addresses come in as -D macros (see tools/build.py).
 */
typedef unsigned int u32;
typedef signed int s32;
typedef unsigned short u16;
typedef signed short s16;
typedef unsigned char u8;
typedef signed char s8;

#define R32(a) (*(volatile u32 *)(a))
#define SI_OUT(c)  (0xCD006400u + (c) * 12)
#define SI_INH(c)  (0xCD006404u + (c) * 12)
#define SI_INL(c)  (0xCD006408u + (c) * 12)
#define SI_POLL    (0xCD006430u)
#define SI_COMCSR  (0xCD006434u)
#define SI_SR      (0xCD006438u)

/* STATE: scheme/combo words used by the cc_*.s hooks live at +0x00/+0x04 */
struct ch {
    u32 probe_tb;   /* last SIGetType */
    u32 prev_btn;   /* Classic Controller buttons of the previous frame's sample */
    u8 norep;       /* consecutive polls with NOREP */
    u8 ours;        /* the last KPAD sample on this channel was ours */
    u8 pad[6];
};
struct ptr {
    float x, y;     /* the virtual pointer, KPAD units (x -1..1, y -0.75..0.75) */
    u32 last_tb;    /* previous update */
    u32 act_tb;     /* last stick movement or button press */
    u32 on;         /* the pointer is shown */
    u32 phase;      /* shake: which way the fake acceleration points */
    u32 res[2];
};
struct st {
    u32 scheme, combo;
    u32 busy_tb;                /* when si:: was first seen busy (0 = idle) */
    u32 res;
    u32 feed[4][2];             /* DEBUG_FEED: pad responses written by a debugger */
    struct ch ch[4];
    struct ptr ptr[4];          /* at +0x80 */
};
#define ST ((volatile struct st *)STATE)

static inline u32 tb(void)
{
    u32 t;
    __asm__ volatile("mftb %0" : "=r"(t));
    return t;
}

/* a valid, error-free pad response on channel c */
static inline int gc_in(u32 c, u32 *h, u32 *l)
{
#ifdef DEBUG_FEED
    if (!ST->feed[c][0])
        return 0;
    *h = ST->feed[c][0];
    *l = ST->feed[c][1];
    return 1;
#else
    u32 v = R32(SI_INH(c));
    if ((v & 0x80000000u) || !(v & 0x00800000u))
        return 0;
    *h = v;
    *l = R32(SI_INL(c));
    return 1;
#endif
}

#if defined(HOOK_POLL)
void gc_poll(u32 chan)
{
    volatile u32 *types = (volatile u32 *)SI_TYPES;
    volatile struct ch *c;
    u32 type, sisr, poll, en, vb, nib;
    int confirmed;
    s32 busy;

    if (chan > 3)
        return;
    c = &ST->ch[chan];
    en = 0x80u >> chan;
    vb = 0x08u >> chan;
    nib = 0x0F000000u >> (8 * chan);

    /* probe the port until a standard pad answers, at most every 0.25 s:
     * probing every frame collides with the pad's own polling on hardware */
    type = types[chan];
    confirmed = !(type & 0x80) && (type & 0x18000000u) == 0x08000000u;
    if (!confirmed) {
        u32 now = tb();
        if (now - c->probe_tb >= 15187500u) {
            c->probe_tb = now;
            ((u32 (*)(u32))FN_SIGETTYPE)(chan);
        }
    }

    /* an unplugged pad latches NOREP; si:: never reads it (no PAD library),
     * so copy a persistent one into the type cache ourselves, which makes
     * SIGetType probe the port again once a pad is plugged back in */
    sisr = R32(SI_SR);
    if (sisr & (0x08000000u >> (8 * chan))) {
        if (c->norep < 10)
            c->norep++;
        else
            types[chan] = 8;
    } else {
        c->norep = 0;
    }

    R32(SI_OUT(chan)) = 0x00400300u;                          /* poll command */
    R32(SI_SR) = (sisr & nib) | (0x80000000u >> (8 * chan)); /* ack errors, latch OUT */

    type = types[chan];
    confirmed = !(type & 0x80) && (type & 0x18000000u) == 0x08000000u;
    poll = R32(SI_POLL) & ~(en | vb);
    if (!(poll & 0xFF00u))
        poll |= 0x0100u;
    R32(SI_POLL) = poll | (confirmed ? (en | vb) : 0);
    /* si:: rewrites SIPOLL from its own shadow on every retrace */
    R32(SI_SHADOW) = (R32(SI_SHADOW) & ~(en | vb)) | (confirmed ? (en | vb) : 0);

    /* a pad unplugged mid-transfer leaves si::'s global busy flag wedged
     * (nothing times it out); force it idle after a second */
    busy = (s32)R32(SI_BUSY);
    if (busy == -1) {
        ST->busy_tb = 0;
    } else {
        u32 now = tb();
        if (ST->busy_tb == 0) {
            ST->busy_tb = now | 1;
        } else if (now - ST->busy_tb >= 60750000u) {
            u32 lvl = ((u32 (*)(void))FN_OSDISABLE)();
            R32(SI_BUSY) = (u32)-1;
            R32(SI_COMCSR) = 0x80000000u;
            ((void (*)(u32))FN_OSRESTORE)(lvl);
            ST->busy_tb = 0;
        }
    }
}
#endif

#if defined(HOOK_SAMPLE)
/* Classic Controller buttons as WPAD reports them */
#define CL_UP    0x0001
#define CL_LEFT  0x0002
#define CL_ZR    0x0004
#define CL_X     0x0008
#define CL_A     0x0010
#define CL_Y     0x0020
#define CL_B     0x0040
#define CL_ZL    0x0080
#define CL_R     0x0200
#define CL_PLUS  0x0400
#define CL_HOME  0x0800
#define CL_MINUS 0x1000
#define CL_L     0x2000
#define CL_DOWN  0x4000
#define CL_RIGHT 0x8000

#define G_A     0x01000000u
#define G_B     0x02000000u
#define G_X     0x04000000u
#define G_Y     0x08000000u
#define G_START 0x10000000u
#define G_Z     0x00100000u
#define G_R     0x00200000u
#define G_L     0x00400000u
#define G_UP    0x00080000u
#define G_DOWN  0x00040000u
#define G_RIGHT 0x00020000u
#define G_LEFT  0x00010000u

static inline s16 stick(u32 raw)
{
    s32 v = ((s32)(raw & 0xFF) - 128) * STICK_SCALE;
    if (v > STICK_MAX)
        v = STICK_MAX;
    if (v < -STICK_MAX)
        v = -STICK_MAX;
    return (s16)v;
}

/* the Classic Controller's right stick is read with a coarser scale than its left one */
static inline s16 cstick(u32 raw)
{
    s32 v = ((s32)(raw & 0xFF) - 128) * STICK_SCALE;
    if (v > CSTICK_MAX)
        v = CSTICK_MAX;
    if (v < -CSTICK_MAX)
        v = -CSTICK_MAX;
    return (s16)v;
}

static __attribute__((noinline)) u32 cc_buttons(u32 h)
{
    u32 b = 0;

    if (h & G_A) b |= CL_A;
    if (h & G_B) b |= CL_B;
    if (h & G_X) b |= CL_X;
    if (h & G_Y) b |= CL_Y;
    if (h & G_L) b |= CL_L;
    if (h & G_R) b |= CL_R;
    if (h & G_UP) b |= CL_UP;
    if (h & G_DOWN) b |= CL_DOWN;
    if (h & G_RIGHT) b |= CL_RIGHT;
    if (h & G_LEFT) b |= CL_LEFT;
    if (h & G_Z) b |= CL_ZL | CL_ZR;         /* ZL + ZR together: shake */
    if (h & G_START) b |= CL_PLUS;
    /* Start + Z is Classic + and - together: swaps the horizontal and vertical layouts */
    if ((h & (G_START | G_Z)) == (G_START | G_Z))
        b = (b & ~(CL_ZL | CL_ZR | CL_PLUS)) | CL_PLUS | CL_MINUS;
    /* HOME: L + R + Start */
    if ((h & (G_L | G_R | G_START)) == (G_L | G_R | G_START))
        b = (b & ~(CL_L | CL_R | CL_PLUS)) | CL_HOME;
    return b;
}

static __attribute__((noinline)) void fill_cc(u8 *s, u32 h, u32 l, u32 b)
{
    *(u16 *)(s + 0x2A) = (u16)b;
    *(s16 *)(s + 0x2C) = stick(h >> 8);      /* control stick x */
    *(s16 *)(s + 0x2E) = stick(h);           /* control stick y */
    *(s16 *)(s + 0x30) = cstick(l >> 24);    /* C-stick x */
    *(s16 *)(s + 0x32) = cstick(l >> 16);    /* C-stick y */
    s[0x34] = (h & G_L) ? 180 : 0;           /* digital L / R: the game reads them only as buttons */
    s[0x35] = (h & G_R) ? 180 : 0;
    s[0x28] = 2;                             /* extension: Classic Controller */
    s[0x29] = 0;                             /* no extension error */
    s[0x40] = 8;                             /* classic + accel + pointer data */
}

/* ring slot i of a channel's KPAD sample queue (the first 16 live in the struct) */
static inline u8 *slot(u8 *k, u32 i)
{
    if (i < 16)
        return k + 0x180 + i * 0x42;
    return *(u8 **)(k + 0x5A0) + (i - 16) * 0x42;
}

static __attribute__((noinline)) void put_sample(u8 *k, u32 i, u32 h, u32 l, u32 b)
{
    u16 *p = (u16 *)slot(k, i);
    u32 j;

    for (j = 0; j < 0x42 / 2; j++)
        p[j] = 0;
    fill_cc((u8 *)p, h, l, b);
}

/* The game's controller class reads the left stick from the *second* status entry KPADRead returns, so one
 * sample per frame leaves it at zero.  A Wii Remote delivers two or three per read; so do we: two samples, the
 * older with the previous frame's buttons (so the press and release edges still land in the newest entry) and
 * both with the current sticks. */
void gc_sample(u8 *k, u32 chan)
{
    u32 h, l, b, i, idx, cnt, n;
    volatile struct ch *c;

    if (chan > 3 || !gc_in(chan, &h, &l))
        return;
    c = &ST->ch[chan];

    b = cc_buttons(h);
    n = 16 + *(u32 *)(k + 0x5A4);   /* ring size */
    idx = k[0x17A];
    cnt = k[0x17B];
    if (idx >= n)
        idx = 0;
    if (cnt == 0) {
        /* no sample queued: no Wii Remote (dev type 0xFD), a bare one that
         * has not delivered one yet, or our own sample showing through */
        u8 dev = k[0x5C];
        if (!(dev == 0 || dev == 0xFD || c->ours))
            return;
        put_sample(k, idx, h, l, c->prev_btn);
        put_sample(k, (idx + 1) % n, h, l, b);
        k[0x17A] = (idx + 2) % n;
        k[0x17B] = 2;
        c->prev_btn = b;
        c->ours = 1;
        return;
    }

    /* real samples queued: a bare Wii Remote gets the pad as its extension;
     * a real Nunchuk or Classic Controller is never touched */
    c->ours = 0;
    c->prev_btn = b;
    if (cnt > n)
        cnt = n;
    for (i = 0; i < cnt; i++) {
        u8 *s = slot(k, (idx + n - cnt + i) % n);
        if (s[0x28] == 0 || s[0x28] == 0xFD)
            fill_cc(s, h, l, b);
    }
    if (cnt == 1) {
        /* a lone real sample: queue a copy after it so there is a second entry */
        u16 *src = (u16 *)slot(k, (idx + n - 1) % n);
        u16 *dst = (u16 *)slot(k, idx);
        if (((u8 *)src)[0x28] == 2) {
            for (i = 0; i < 0x42 / 2; i++)
                dst[i] = src[i];
            k[0x17A] = (idx + 1) % n;
            k[0x17B] = 2;
        }
    }
}
#endif

#if defined(HOOK_PROBE)
/* WPADProbe(chan, &type): report a Classic Controller on the channel while a
 * pad is plugged in, unless the channel already has a real extension */
u32 gc_probe(u32 chan, u32 *type)
{
    u32 h, l;
    u8 *blk;
    u32 t;
    s32 status;

    if (chan > 3 || !gc_in(chan, &h, &l))
        return 0;
    blk = *(u8 **)(WPAD_TBL + chan * 4);
    t = blk[2309];
    status = *(s32 *)(blk + 2304);
    if (status != -1 && (t == 1 || t == 2))
        return 0;
    if (type)
        *type = 2;
    return 1;
}
#endif

#if defined(HOOK_PTR1) || defined(HOOK_PTR2)
/* The Classic Controller has no pointer and no motion, but Wii Party's games use both.  Called after KPAD has
 * processed each sample (before it is copied into the caller's status entry): the right stick moves a virtual
 * IR pointer, and ZL + ZR together (GameCube: Z) fake a shake.  Real Wii Remote data is never touched: only
 * Classic Controller samples (device type 2) come here.  Hard float; no constants in memory.
 * k = the channel's KPAD struct, entry = the sample being processed. */
static inline float F(u32 u)
{
    union { u32 u; float f; } x;
    __asm__("" : "+r"(u));          /* keeps the constant out of .rodata: the bodies are position independent */
    x.u = u;
    return x.f;
}
static inline u32 U(float f)
{
    union { u32 u; float f; } x;
    x.f = f;
    return x.u;
}

void cc_ptr(u8 *k, u32 chan, u8 *entry)
{
    volatile struct ptr *p;
    float rx, ry, px, py, dt;
    u32 now, dt_tb, moved, btn;

    if (chan > 3 || k[0x5C] != 2)
        return;
    p = &ST->ptr[chan];
    now = tb();
    dt_tb = now - p->last_tb;
    p->last_tb = now;
    if (dt_tb > 4050000u)
        dt_tb = 4050000u;                         /* first sample, or the game paused: 0.1 s at most */
    dt = (F(0x4B000000u | dt_tb) - F(0x4B000000u)) * F(0x32D418DFu);   /* seconds */

    btn = *(u16 *)(entry + 0x2A);                  /* the Classic buttons as the sample carries them */
    rx = *(float *)(k + 0x74);
    ry = *(float *)(k + 0x78);
    moved = (U(rx) & 0x7FFFFFFFu) > 0x3E19999Au || (U(ry) & 0x7FFFFFFFu) > 0x3E19999Au;   /* > 0.15 */

    if (moved || btn) {
        if (!p->on && moved) {
            p->x = F(0);
            p->y = F(0);
        }
        p->act_tb = now;
    }
    if (moved) {
        p->on = 1;
        px = p->x + rx * dt * F(PTR_SPEED_X);
        py = p->y - ry * dt * F(PTR_SPEED_Y);      /* KPAD y grows downwards */
        if (px > F(0x3F800000u)) px = F(0x3F800000u);
        if (px < F(0xBF800000u)) px = F(0xBF800000u);
        if (py > F(0x3F400000u)) py = F(0x3F400000u);
        if (py < F(0xBF400000u)) py = F(0xBF400000u);
        p->x = px;
        p->y = py;
    }
    if (p->on && now - p->act_tb > 607500000u)    /* 15 s idle: hand the pointer back to the menus */
        p->on = 0;
    if (p->on) {
        *(float *)(k + 0x20) = p->x;
        *(float *)(k + 0x24) = p->y;
        k[0x5E] = 1;
    }

    if ((btn & 0x84) == 0x84) {                   /* ZL + ZR: shake */
        float a = p->phase ? F(0x40800000u) : F(0xC0800000u);
        p->phase ^= 1;
        *(float *)(k + 0x0C) = a;
        *(float *)(k + 0x10) = a;
        *(float *)(k + 0x14) = a;
    }
}
#endif
