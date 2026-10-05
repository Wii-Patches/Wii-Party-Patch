"""Wii Party releases and the game addresses the patches need.

USA (SUPE01) is the reference, found by hand in its main.dol; the other releases
are located from it by tools/anchors.py when the prebuilt data is regenerated.
"""
LOW = 0x80001820          # new text section for the hook bodies (static patch)
STATE = 0x80005E78        # the shared state block: zero padding in the retail main.dol of every release
STATE_SIZE = 0x200

# One entry per distinct main.dol.  The European disc ships the very same main.dol as the American one.
# `discs` are (disc id, disc version) pairs that carry it; `dol` is the file name tools/build.py looks for
# in its --dols directory.
REGIONS = {
    'SUPE01': {'label': 'USA / Europe', 'short': 'USA, Europe', 'dol': 'SUPE01.dol', 'reference': True,
               'discs': [('SUPE01', 0), ('SUPP01', 0)]},
    'SUPJ01': {'label': 'Japan', 'short': 'Japan', 'dol': 'SUPJ01.dol', 'discs': [('SUPJ01', 0)]},
    'SUPJ01v1': {'label': 'Japan (Rev 1)', 'short': 'Japan Rev 1', 'dol': 'SUPJ01v1.dol',
                 'discs': [('SUPJ01', 1)]},
    'SUPK01': {'label': 'Korea', 'short': 'Korea', 'dol': 'SUPK01.dol', 'discs': [('SUPK01', 0)]},
}


def region_of_disc(disc_id, version):
    for key, r in REGIONS.items():
        if (disc_id, version) in r['discs']:
            return key
    return None

# USA addresses ---------------------------------------------------------------------------------
# (name, address, the retail word that must be there)
USA_SITES = {
    # Classic Controller (Vague Rant's hack + the left-stick D-pad and tilt hooks)
    'cc_buttons': (0x80190524, 0x70C09FFF),     # andi. r0,r6,0x9FFF   (read_kpad_button)
    'cc_stick':   (0x801925D0, 0x4E800421),     # bctrl                (read_kpad_stick)
    'cc_tilt':    (0x80190848, 0x90010044),     # stw r0,68(r1)        (calc_acc_vertical)
    'cc_ptr1':    (0x801939AC, 0x38B2FFFC),     # addi r5,r18,-4       (KPADiRead: status copy, first loop)
    'cc_ptr2':    (0x80193B6C, 0x38B3FFFC),     # addi r5,r19,-4       (KPADiRead: status copy, second loop)
    # GameCube controllers
    'gc_poll':    (0x801934E0, 0x9421FDC0),     # stwu r1,-576(r1)     (KPADiRead entry)
    'gc_sample':  (0x80193684, 0x8815017B),     # lbz r0,379(r21)      (KPADiRead sample count)
    'gc_probe':   (0x8017C9E0, 0x9421FFF0),     # stwu r1,-16(r1)      (WPADProbe entry)
}
USA_DEFS = {
    'SI_TYPES':     0x8021F818,
    'SI_BUSY':      0x8021F800,
    'SI_SHADOW':    0x8021F804,
    'FN_SIGETTYPE': 0x801462F0,
    'FN_OSDISABLE': 0x8013C030,
    'FN_OSRESTORE': 0x8013C070,
    'WPAD_TBL':     0x802B62D0,
}
