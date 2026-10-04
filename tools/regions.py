"""Wii Party releases and the game addresses the patches need.

USA (SUPE01) is the reference, found by hand in its main.dol; the other releases
are located from it by tools/anchors.py when the prebuilt data is regenerated.
"""
LOW = 0x80001820          # new text section: the shared state block, then the hook bodies
STATE = LOW
STATE_SIZE = 0x100

REGIONS = {
    'SUPE01': {'label': 'USA', 'reference': True},
}

# USA addresses ---------------------------------------------------------------------------------
# (name, address, the retail word that must be there)
USA_SITES = {
    # Classic Controller (Vague Rant's hack + the left-stick D-pad and tilt hooks)
    'cc_buttons': (0x80190524, 0x70C09FFF),     # andi. r0,r6,0x9FFF   (read_kpad_button)
    'cc_stick':   (0x801925D0, 0x4E800421),     # bctrl                (read_kpad_stick)
    'cc_tilt':    (0x80190848, 0x90010044),     # stw r0,68(r1)        (calc_acc_vertical)
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
