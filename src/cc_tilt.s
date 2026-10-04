# Classic left stick as Wii Remote tilt -- site 0x80190848 (USA), the displaced stw is first
# calc_acc_vertical
# 80190848 for USA
stw r0, 0x44(sp)
  lbz r0, 0x5C(r3)
  cmpwi r0, 0x2
  bne- RETURN

CLASSIC_TILT:
  bl GRAB
MAGIC:
    RANGE:  .float   0.8
GRAB:
  mflr r5
  lfs f0, RANGE-MAGIC(r5)
  lfs f1, 0x6C(r3)      # classic LEFT stick X
  fmuls f0, f0, f1
  stfs f0, 0x58(r3)
  fneg f2, f1              # CHANGED: flip sign for cloud left/right
  stfs f2, 0x14(r3)
  lfs f1, 0x70(r3)         # classic LEFT stick Y
  stfs f1, 0x0C(r3)          # cloud up/down (unchanged, already correct)
  b DONE

DONE:
  lwz r0, 0x44(sp)
  mtlr r0
  addi sp, sp, 0x40
  blr
RETURN:
  nop
