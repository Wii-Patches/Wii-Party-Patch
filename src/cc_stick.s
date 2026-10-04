# Classic left stick as D-pad (menus) -- site 0x801925d0 (USA), the displaced bctrl is first
# read_kpad_stick
# 801925d0 for USA
  bctrl
  cmpwi r22, 0x1
  bne- RETURN

# magic
  bl GRAB
MAGIC:
    THRESHOLD:  .float 0.5
    ZERO:       .float 0.0
GRAB:
  mflr r3

  lfs f2, THRESHOLD-MAGIC(r3)
  lfs f3, ZERO-MAGIC(r3)
  lwz r4, -0x60(r30)
  lwz r5, -0x5C(r30)
  lwz r6, -0x58(r30)

  lis r11, STATE>>16
  ori r11, r11, STATE&0xFFFF
  lwz r11, 0(r11)          # SCHEME: r11 = 0 (vertical) or 1 (horizontal)

  lfs f1, 0x0C(r30)
  li r8, 0x1
  bl STICK_EMULATION

  lfs f1, 0x10(r30)
  li r8, 0x4
  bl STICK_EMULATION
  stw r4, -0x60(r30)
  stw r5, -0x5C(r30)
  stw r6, -0x58(r30)
  b RETURN

STICK_EMULATION:
  fabs f0, f1
  fcmpo cr0, f0, f2
  bltlr-

  fcmpo cr0, f1, f3
  blt- AXIS_SKIP
  slwi r8, r8, 0x1

AXIS_SKIP:
  cmpwi r11, 0
  beq- APPLY_BITS

  cmpwi r8, 0x1
  bne- ROT2
  li r8, 0x8
  b APPLY_BITS
ROT2:
  cmpwi r8, 0x2
  bne- ROT4
  li r8, 0x4
  b APPLY_BITS
ROT4:
  cmpwi r8, 0x4
  bne- ROT8
  li r8, 0x1
  b APPLY_BITS
ROT8:
  li r8, 0x2

APPLY_BITS:
  and. r0, r6, r8
  bne- NOT_NEW
  or r5, r5, r8

NOT_NEW:
  or r4, r4, r8
  andc. r6, r6, r8

  blr

RETURN:
  nop
