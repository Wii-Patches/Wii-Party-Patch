# Wii Party Patch

Play **Wii Party** (Wii) with a **GameCube controller** or a **Classic
Controller** instead of a Wii Remote. Works with the USA / European
(`SUPE01`, `SUPP01`), Japanese (`SUPJ01`, both revisions) and Korean
(`SUPK01`) releases.

The patches are applied to your own copy of the game: drop a clean `.wbfs` or
`.iso` onto the patcher and play the result on a Wii (USB loader) or in
Dolphin. Nothing from the game is included in this repository.

![Wii Party](assets/logo.png)

## Status

Tested in Dolphin only (scripted GameCube pad input, USA release): menus and
the D-pad, the pad as players 1-4, pointer menus, a minigame. The other
releases are patched at addresses found by matching the USA code; they are
checked to patch cleanly but have not been booted. **Not tested on a real
Wii** — see [On a real Wii](#on-a-real-wii).

## Controls

### Classic Controller

The Classic Controller layout is Vague Rant's hack, extended with a D-pad /
tilt / pointer layer. `+` and `-` together switch between the two layouts
(Wii Remote held **vertically**, which is the default, or **sideways**), the
same way Wii Party's own minigames ask for them.

| Input | Action |
| --- | --- |
| Left stick | Menu D-pad · Wii Remote tilt (minigames) |
| Right stick | Pointer (appears when you move it; hands back to the menu cursor after 15 s idle) |
| D-pad, A, B, X, Y, L, R, ZL, ZR, +, − | Wii Remote buttons (layout depends on the vertical/sideways scheme) |
| HOME | HOME Menu |
| + and − together | Switch between the vertical and sideways layouts |

### GameCube controller

Plug a pad into any of the four ports; **port N drives player N**. No Wii
Remote is needed for a player whose port has a pad: the pad shows up to the
game as a Classic Controller, so it gets exactly the layer above.

| GameCube | Classic Controller |
| --- | --- |
| Control stick | Left stick |
| C-stick | Right stick (pointer) |
| A, B, X, Y | A, B, X, Y |
| L, R | L, R |
| D-pad | D-pad |
| Start | + |
| Z | Shake (the Wii Remote's own motion, faked: for the shake minigames) |
| Start + Z | + and − together: switch vertical / sideways |
| L + R + Start | HOME |

## Installing

### Patch your disc image

You need a clean `.wbfs` or `.iso`. Run the patcher (needs Python 3 with
tkinter and [Wiimms ISO Tool](https://wit.wiimm.de/) (`wit`) on your `PATH`):

```bash
python3 tools/gui.py
```

Tick the patches you want, then drop the image onto the window (or click to
choose it). The patcher checks the disc id, patches `sys/main.dol`, rebuilds
the image in the same format and replaces your file, keeping the original next
to it as `<name>.bak`. Other releases, and images already modified by something
else, are refused rather than corrupted.

Command line twin:

```bash
python3 tools/patch_disc.py "Wii Party (USA) (En,Fr,Es).wbfs" --cc --gc
```

Or patch a bare `main.dol`:

```bash
python3 tools/patcher.py <retail main.dol> <patched main.dol> --cc --gc
```

## On a real Wii

- Play the patched image from a USB loader as usual. Turn the loader's
  **cheats / debugger off** for this game: its code handler shares the memory
  the patch lives in.
- Connect the GameCube controller **before** launching the game; hot-plugging
  is handled but only lightly tested.
- With a pad in a port you do not need a Wii Remote for that player. A Wii
  Remote that *is* connected keeps working next to it.
- With a Classic Controller you still need its Wii Remote, as the controller
  plugs into it.

## Building from source

The patcher itself needs only Python 3 and `wit`. The routines it injects ship
pre-assembled in `tools/prebuilt/` (checked by `tools/check.py`). To rebuild
them you need [devkitPPC](https://devkitpro.org/) and your own `main.dol`
dumps of each release:

```bash
python3 tools/build.py --dols /dir/with/SUPE01.dol,SUPJ01.dol,SUPJ01v1.dol,SUPK01.dol
python3 tools/check.py        # consistency checks (no game files needed)
```

How the patches work, and how they are tested in Dolphin, is in
[docs/TECHNICAL.md](docs/TECHNICAL.md).

## Credits

- **Vague Rant** — the Classic Controller hack for Wii Party this layer is built on
  ([GBAtemp thread](https://gbatemp.net/threads/new-classic-controller-hacks.659837/)),
  and the follow-up button, D-pad and tilt hooks in `src/cc_*.s`.
- The SI-polling approach of
  [Barrel Blast Patch](https://github.com/quatric/Barrel-Blast-Patch), reused through
  [ACCF-Patch](https://github.com/quatric/ACCF-Patch).
- Wiimms ISO Tool, for reading and writing the disc images.

## Contact

quatricsoftware@gmail.com

No support will be provided for this tool.

## License

MIT — see [LICENSE](LICENSE).

Copyright (c) 2026 quatric
