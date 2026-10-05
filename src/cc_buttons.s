# Classic Controller buttons -> Wii Remote bits (Vague Rant's hack, scheme switch by +/- together)
# site 0x80190524 (USA)# the displaced andi. r0,r6,0x9FFF is at RETURN
.set SCHEME, 0
.set COMBO_HELD, 4
# read_kpad_button
# 80190524 (USA)

CLASSIC:
  cmpwi r4, 0x2
  bne-  RETURN

  # ZL + ZR together are a shake (cc_ptr): keep them from also pressing A and B
  andi. r0, r8, 0x84
  cmpwi r0, 0x84
  bne-  NOT_SHAKE
  andi. r8, r8, 0xFF7B
  NOT_SHAKE:
  # r12 = the shared state block (STATE+0 SCHEME, STATE+4 COMBO_HELD)
  lis   r12, STATE>>16
  ori   r12, r12, STATE&0xFFFF

  # --- Combo Detection (Plus + Minus = 0x1400) using r11 ---
  andi. r11, r8, 0x1400
  cmpwi r11, 0x1400
  bne-  NO_COMBO

  # Check if combo was already held
  lwz   r11, COMBO_HELD(r12)
  cmpwi r11, 0
  bne-  CONTINUE

  # Edge detected! Flip scheme
  lwz   r11, SCHEME(r12)
  xori  r11, r11, 1
  stw   r11, SCHEME(r12)

  li    r11, 1
  stw   r11, COMBO_HELD(r12)
  b     CONTINUE

NO_COMBO:
  li    r11, 0
  stw   r11, COMBO_HELD(r12)

CONTINUE:
  lwz   r11, SCHEME(r12)
  cmpwi r11, 0
  beq-  CLASSIC_VERTICAL
  b     CLASSIC_HORIZONTAL

CLASSIC_VERTICAL:
  CLASSIC_HOME_V:
      andi. r0, r8, 0x800
      beq- CLASSIC_UP_V
      ori r6, r6, 0x8000    # home
    CLASSIC_UP_V:
      andi. r0, r8, 0x1
      beq- CLASSIC_DOWN_V
      ori r6, r6, 0x8       # up
    CLASSIC_DOWN_V:
      andi. r0, r8, 0x4000
      beq- CLASSIC_LEFT_V
      ori r6, r6, 0x4       # down
    CLASSIC_LEFT_V:
      andi. r0, r8, 0x2
      beq- CLASSIC_RIGHT_V
      ori r6, r6, 0x1       # left
    CLASSIC_RIGHT_V:
      andi. r0, r8, 0x8000
      beq- CLASSIC_A_V
      ori r6, r6, 0x2       # right
    CLASSIC_A_V:
      andi. r0, r8, 0x10
      beq- CLASSIC_B_V
      ori r6, r6, 0x800     # A
    CLASSIC_B_V:
      andi. r0, r8, 0x40
      beq- CLASSIC_X_V
      ori r6, r6, 0x400     # B
    CLASSIC_X_V:
      andi. r0, r8, 0x8
      beq- CLASSIC_Y_V
      ori r6, r6, 0x100     # 2
    CLASSIC_Y_V:
      andi. r0, r8, 0x20
      beq- CLASSIC_L_V
      ori r6, r6, 0x200     # 1
    CLASSIC_L_V:
      andi. r0, r8, 0x2000
      beq- CLASSIC_R_V
      ori r6, r6, 0x400     # B
    CLASSIC_R_V:
      andi. r0, r8, 0x200
      beq- CLASSIC_ZL_V
      ori r6, r6, 0x800     # A
    CLASSIC_ZL_V:
      andi. r0, r8, 0x80
      beq- CLASSIC_ZR_V
      ori r6, r6, 0x400     # B
    CLASSIC_ZR_V:
      andi. r0, r8, 0x4
      beq- CLASSIC_SHARED
      ori r6, r6, 0x800     # A
      b CLASSIC_SHARED

CLASSIC_HORIZONTAL:
  CLASSIC_HOME_H:
      andi. r0, r8, 0x800
      beq- CLASSIC_UP_H
      ori r6, r6, 0x8000    # home
    CLASSIC_UP_H:
      andi. r0, r8, 0x1
      beq- CLASSIC_DOWN_H
      ori r6, r6, 0x2       # up (adjust rotation here if needed)
    CLASSIC_DOWN_H:
      andi. r0, r8, 0x4000
      beq- CLASSIC_LEFT_H
      ori r6, r6, 0x1       # down
    CLASSIC_LEFT_H:
      andi. r0, r8, 0x2
      beq- CLASSIC_RIGHT_H
      ori r6, r6, 0x8       # left
    CLASSIC_RIGHT_H:
      andi. r0, r8, 0x8000
      beq- CLASSIC_A_H
      ori r6, r6, 0x4       # right
    CLASSIC_A_H:
      andi. r0, r8, 0x10
      beq- CLASSIC_B_H
      ori r6, r6, 0x100     # 2
    CLASSIC_B_H:
      andi. r0, r8, 0x40
      beq- CLASSIC_X_H
      ori r6, r6, 0x200     # 1
    CLASSIC_X_H:
      andi. r0, r8, 0x8
      beq- CLASSIC_Y_H
      ori r6, r6, 0x800     # A
    CLASSIC_Y_H:
      andi. r0, r8, 0x20
      beq- CLASSIC_L_H
      ori r6, r6, 0x400     # B
    CLASSIC_L_H:
      andi. r0, r8, 0x2000
      beq- CLASSIC_R_H
      ori r6, r6, 0x200     # 1
    CLASSIC_R_H:
      andi. r0, r8, 0x200
      beq- CLASSIC_ZL_H
      ori r6, r6, 0x100     # 2
    CLASSIC_ZL_H:
      andi. r0, r8, 0x80
      beq- CLASSIC_ZR_H
      ori r6, r6, 0x200     # 1
    CLASSIC_ZR_H:
      andi. r0, r8, 0x4
      beq- CLASSIC_SHARED
      ori r6, r6, 0x100     # 2

CLASSIC_SHARED:
  # --- Clean Plus & Minus mapping without r0 corruption ---
  CLASSIC_PLUS:
    andi. r0, r8, 0x400
    beq-  CLASSIC_MINUS
    ori   r6, r6, 0x10          # Plus

  CLASSIC_MINUS:
    andi. r0, r8, 0x1000
    beq-  RETURN
    ori   r6, r6, 0x1000        # Minus

RETURN:
  andi. r0, r6, 0x9FFF
  nop
