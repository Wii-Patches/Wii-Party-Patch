# Technical notes

How the patches work, and how they are tested. For installing and playing, see
the [README](../README.md). Addresses are the **USA / Europe** `main.dol`
(`SUPE01`, identical in `SUPP01`) unless noted; `tools/anchors.py` finds the
same code in the Japanese and Korean releases.

## Where the input goes

Wii Party reads every controller through the SDK's `KPAD` library:
`KPADiRead` (`0x801934E0`) takes the samples `WPAD` queued for a channel
(a ring of 16 × `0x42` bytes at `+0x180` of the channel's `KPAD` struct, base
`0x802BC488`, stride `0x688`), runs them through the per-extension decoders,
and copies the result into the 240-byte status entries it hands to the game.
A sample says what is plugged into the remote: `+0x28` is the extension
(`2` = Classic Controller), `+0x29` its error byte, `+0x2A` the Classic buttons,
`+0x2C..+0x32` the two sticks, `+0x40` the data format.

Everything here works on those samples and on the decoded values, so the game
itself never needs to know a different controller is plugged in.

## Classic Controller

Vague Rant's hack makes the game's Classic Controller path usable. The files
`src/cc_*.s` are the three pieces, hooked with a branch to a body that runs the
displaced instruction and branches back:

| Hook | Site | What it does |
| --- | --- | --- |
| `cc_buttons` | `0x80190524` | Classic buttons → Wii Remote bits, in the *vertical* or *sideways* layout. `+` and `-` together flip the layout (`STATE+0`), edge-triggered by `STATE+4` |
| `cc_stick` | `0x801925D0` | Left stick → D-pad bits (menus), rotated for the sideways layout |
| `cc_tilt` | `0x80190848` | Left stick → the acceleration fields the tilt minigames read (`calc_acc_vertical`) |
| `cc_ptr1`, `cc_ptr2` | `0x801939AC`, `0x80193B6C` | Right stick → a virtual IR pointer (see below). Runs just before KPAD copies the sample into the caller's status entry |

The pointer is integrated from the right stick (about 1.6 and 1.2 screens per
second at full deflection), shown as soon as the stick moves, and handed back to
the menu cursor after 15 s without input. Only Classic Controller samples
(`k[0x5C] == 2`) are touched, so a real Wii Remote's pointer is never replaced.

## GameCube controllers

The game links the SI library but not `PAD`, so nothing polls the pads and a
game with no Wii Remote has no `KPAD` samples. Three hooks (`src/gcpad.c`,
`src/hooks.S`) change that; the technique is
[Barrel Blast Patch](https://github.com/quatric/Barrel-Blast-Patch)'s, as
reused in [ACCF-Patch](https://github.com/quatric/ACCF-Patch):

| Hook | Site | What it does |
| --- | --- | --- |
| `gc_poll` | `KPADiRead` entry | Turns on the SI hardware's auto-poll for the channel (`0xCD006400`, the Wii mirror, not `0xCC`), probes an empty port at most every 0.25 s, acknowledges `NOREP`, mirrors the enable bits into the SDK's shadow of `SIPOLL`, and unwedges a stuck "transfer busy" flag |
| `gc_sample` | `KPADiRead`, the sample-count check | Writes two Classic Controller samples into the channel's ring (the game reads the left stick from the *second* status entry), unless a real Classic Controller or Nunchuk is already there |
| `gc_probe` | `WPADProbe` entry | Reports a Classic Controller on the channel while a pad answers, so the game counts the player as connected |

Port N feeds channel N. The pad's response is decoded straight from
`SIC0INBUFH/L` (`+12` per port); it is valid when the error bit is clear and
bit 23 is set.

**Z** is a shake: the sample's raw acceleration swings between two large values
about 4 times a second. The game's motion analysis (`0x80069200`, with an FFT in
`0x800697D0`) works on a history of the acceleration, so a swing at the
frame rate (the first attempt) is outside its band. Whether this one registers
in the shake minigames is **not yet verified**.

## Where the code lives

The static patch adds one text section at `0x80001820` (clear of the OS globals
at `0x80003000`, and not `0x80001800`, where a loader's code handler sits) holding
the hook bodies. The state block (`0x80005E78`, `0x200` bytes: layout flags,
per-port timers and pointer positions) is zero padding in the retail text
section of every release, so the section holds code only and the patcher can
refuse a DOL whose state area is not zero.

## Releases

`tools/anchors.py` locates each hook by matching a window of USA instructions
against the other DOL with every relocatable bit (branch displacements,
address halves, small-data offsets) masked out; it must match exactly once, and
data addresses are read back from the matched code, never guessed.

| main.dol | Discs |
| --- | --- |
| `SUPE01` | `SUPE01`, `SUPP01` (the same file) |
| `SUPJ01` | `SUPJ01` rev 0 |
| `SUPJ01v1` | `SUPJ01` rev 1 |
| `SUPK01` | `SUPK01` |

## Testing in Dolphin (`lab/`)

`lab/lab.py` boots a disc in a private Dolphin user folder with the GDB stub
on, and `lab/labd.py` keeps it running and takes commands (`lab/ctl.py`).
`tools/build.py --debug-feed` builds hooks whose pad responses come from a
state word a debugger writes, so button presses, sticks and shakes can be
scripted deterministically; `ctl.py reload` pokes a freshly built set of hooks
into the running game. `lab/flows.py` walks the menus by comparing the frame
against reference screens (`lab/refs/`), rather than counting frames.

```bash
python3 tools/build.py --dols DIR --debug-feed
python3 tools/patcher.py main.dol feed.dol --feed     # then rebuild a wbfs with wit
python3 lab/labd.py feed.wbfs &
python3 lab/flows.py race
```
