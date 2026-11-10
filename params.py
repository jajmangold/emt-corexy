# -*- coding: utf-8 -*-
"""EMT CoreXY 300x300x400 - parameters, derived geometry, and hard checks.

X axis: a single MGN12 rail on a 2020 extrusion, carrying a stock Voron
Stealthburner + Clockwork 2.5. All Voron geometry here is MEASURED off the
official CAD (CAD/Stealthburner_CW2.5_Assembly.step, imported with ImportGui).
The X axis has been converted from two 12 mm rods to a single MGN12 rail on a
2020 extrusion, to carry a stock Voron Stealthburner + Clockwork 2.5. All the
Voron geometry here is MEASURED off the official CAD. params.check() passes,
The Z rods cantilever - see the note at the end of this file for why.

Frame is 1/2 inch EMT electrical conduit only; every joint is a printed pinch
clamp. All motion is on hardened linear rod. Controller is a BTT SKR Pico
(4x TMC2209: X, Y, Z1+Z2 PARALLELED on one driver, E).

Coordinate system
    X right, Y rear-positive, Z up.
    Origin X=Y=0 at the centre of the build area.
    Z=0 at the BOTTOM FRAME PLANE (bottom rail centrelines). Feet hang below.

Key layering decisions (these are what make the gantry buildable):

  1. Both belts turn at the SAME (X,Y) on each side, stacked in Z - one idler
     stud per Y carriage, one coaxial station per rear corner. Both beam runs
     also share one Y, so the two belt forces apply no yaw couple.
  2. The rear corners carry a motor and the other belt's idler coaxially, so
     the motors mount in opposite senses to stay out of each other's way:
       belt A plane 645, motor SHAFT DOWN with the body ABOVE (659..707)
       belt B plane 591, motor SHAFT UP   with the body BELOW (529..577)
  3. The X axis is a single MGN12 rail on a 2020 extrusion, because that is
     what a Voron Stealthburner + Clockwork 2 is built around. TOOL_DROP is
     therefore 50.91 - measured off the official CAD, not guessed - and the
     bed/Z subsystem shifts forward by BED_Y so the forward-hanging nozzle
     still sweeps the bed symmetrically.
"""
import math

OV = 0.3          # mandatory overlap on every printed union - never tangent
                  # (freecad-tangent-non-manifold: tangency -> open STL)

# ------------------------------------------------------------------ conduit
EMT_OD   = 17.93          # 1/2 in EMT true OD (0.706 in)
EMT_WALL = 1.07           # 0.042 in
EMT_FIT  = 0.45           # socket bore clearance; the pinch bolt takes it up
EMT_BORE = EMT_OD + EMT_FIT
EMT_GAP  = 0.5            # air gap where a rail meets a post. Was 2.0, which
                          # meant the rail floated clear and the collar carried
                          # everything on friction (fine - ~1.9 kN of grip from
                          # one M4 against member loads of tens of N - but there
                          # was no compression path at all). Closed up to 0.5 so
                          # the butt actually bears, which needs accurate square
                          # cuts; see the cutting notes in the README.

# ------------------------------------------------------------- build volume
BUILD_X, BUILD_Y, BUILD_Z = 300.0, 300.0, 400.0
# Sized to a real part: POLISI / CR-10 310x310x3 mm aluminium heatbed,
# 24 V 220 W, mounting holes on a 240 mm square, 4.2 mm dia.
BED_PLATE   = 310.0       # square bed assembly
BED_PLATE_T = 3.0         # aluminium plate - 3 mm, NOT the 6 I first assumed
BED_STACK   = 2.0         # magnet sheet + spring steel PEI on top
BED_HOLE    = 120.0       # +- ; the bed's own 240 mm square hole pattern
BED_HOLE_D  = 4.2         # the holes in the plate; take M4
BED_W, BED_V = 220.0, 24.0
# Where a BedMount bolts to the carriage pad. The pad spans X 150..201 but the
# carriage SPINE sits under X 169..201, so the only strip where a bracket
# flange can tuck under the pad is X 150..169 - both bolts live there.
BM_BOLT = ((158.0, 48.0), (158.0, 68.0))
BM_FLANGE_X1 = 167.0

# -------------------------------------------------------------------- frame
POST_X  = 245.0
POST_Y  = 275.0           # deeper than wide: the A/B motors live behind the
                          # Y-carriage sweep, which needs the room
Z_FOOT    = -78.0
Z_BOT     =   0.0         # bottom rectangle + 2 cross rails
Z_MID     = 300.0         # FRONT mid rail only - post tie + electronics
# Z_ZTOP and its side rails are GONE - the Z rods cantilever. Kept only as a
# dead constant because a few derived expressions still read it.
Z_ZTOP    = 515.0
# The gantry stiffener rectangle is GONE: with the frame triangulated it added
# little, and in the side planes it sat squarely in the diagonals' path. Only
# its height is kept, as the anchor datum some older code still reads.
Z_GANTRY  = 440.0
Z_CAP     = 690.0         # top cap rectangle: spool, enclosure
Z_WIPE    = 460.0         # front cross rail carrying the nozzle wipe station
POST_LEN  = Z_CAP - Z_FOOT
RAIL_X_LEN = 2 * POST_X - EMT_OD - 2 * EMT_GAP   # rails running along X
RAIL_Y_LEN = 2 * POST_Y - EMT_OD - 2 * EMT_GAP   # rails running along Y

# ---------------------------------------------------------------- bracing
# A rectangle of tube on pinch clamps is a four-bar mechanism: its racking
# stiffness comes only from joint ROTATIONAL stiffness, which is exactly what
# a clamp on round tube is worst at. Measured for one 550x560 side bay:
#   unbraced, ideal rigid corners     55 N/mm
#   + a mid rail (two storeys)       221 N/mm   (x4,  and only if corners are rigid)
#   one diagonal, axial             7090 N/mm   (x128, independent of joint rigidity)
# So the mid rectangle is replaced by real triangulation. Only the FRONT mid
# rail is kept, as a post tie and electronics shelf; the front plane stays
# diagonal-free for access.
#
# Diagonal end nodes are inset from the post axes because each end lands on a
# BraceTang clamped to the post, not on the post centreline.
BRACE_NODE   = 22.0      # node offset from the post axis
# Side brace tops USED to stop at 460, clear of the TeeZTop post clamps
# (485..531) and the Z_ZTOP rail - both of which are now deleted. Raised to
# 545, just under where the Y carriage starts sweeping the x=+-POST_X plane
# (z=567). That matters a lot: gantry load enters the posts at the Y-rod
# blocks (z=630) and reaches the brace node through POST BENDING, so moving
# the node from 460 to 545 cuts that cantilever from 170 mm to 85 mm and
# stiffens the interface about 8x (247 -> 1975 N/mm).
SIDE_BR_Z0, SIDE_BR_Z1 = 40.0, 545.0
REAR_BR_Z0, REAR_BR_Z1 = 40.0, 460.0
REAR_UP_X = 185.0        # rear diagonals: inboard of the Joint4 X-sockets
CAP_BR_A  = 120.0        # cap plan corner braces, offset along each rail
BRACE_OFF = EMT_OD + 3.0 # rail-anchored brace offset: a bare EMT_OD leaves the
                         # two tubes exactly TANGENT, which is the one thing
                         # never to do (freecad-tangent-non-manifold)
TANG_T       = 10.0      # tang plate thickness
BRACE_CL     = 20.0      # brace-clamp centre, measured along the brace
M6, M6_HEAD  = 6.4, 11.0

# ------------------------------------------------------------- Z (bed) axis
# The toolhead hangs FORWARD of the beam, so the nozzle is SB_NOZZLE_FWD
# ahead of the gantry centre. Rather than grow the frame backwards to let the
# gantry travel that far, the whole bed / Z subsystem shifts forward by the
# same amount - then the gantry still sweeps a symmetric +-BUILD_Y/2.
BED_Y      = -52.10  # = -(extrusion centre to nozzle), MEASURED
ZSCREW_X   = 196.0   # clear of the MEASURED 76.4 mm toolhead at +-150 X,
                     # and 3.5 mm clear of the cross-rail end collar
ZROD_X     = 196.0
ZROD_Y     =  55.0
ZROD_D     =  10.0
ZROD_Z0    =  25.0
ZROD_LEN   = 480.0   # cut from 500 stock. The rods CANTILEVER - there is no
                     # top support any more, see the note at the end of this file
ZSCREW_D   =   8.0        # T8, 2 mm pitch x 4 start = 8 mm/rev
ZSCREW_Z0  =  13.0
ZSCREW_LEN = 500.0        # top end free - no top bearing
ZCROSS_Y   =  60.0        # bottom cross rails (along X) carrying Z motors
ZMOT_FACE  = -14.0        # Z motor mounting face (shaft up, body below)
BED_RISE   =  43.0        # nut centre -> print surface
# NUT_LOW / NUT_HIGH are DERIVED from the nozzle height further down: the
# nozzle sets where the bed's top of travel has to be, not the other way round.

# ------------------------------------------------------------------- gantry
YROD_D, YROD_X, YROD_Z = 12.0, 248.0, 630.0
YROD_GRIP = 24.0   # how much of each Y rod end the block actually holds
YROD_LEN = 500.0   # stock length - cheap in pairs
# X AXIS IS A SINGLE MGN12 RAIL ON A 2020 EXTRUSION, not two rods. That is what
# Stealthburner is designed around, and the measured assembly gives the exact
# cross-section: relative to the beam axis the extrusion is centred (+-10 in
# both Y and Z) and the rail sits on its FRONT face, Y -18..-10, Z -6..+6.
# It also fixes the rod slop: two LM12UU on round rod turn 0.02-0.05 mm of play
# into 0.08-0.19 mm of nozzle wander, while an MGN12H block is preloaded.
XBEAM_Z   = 559.0        # chosen so NOZZLE_Z lands back on ~508 and the
                         # whole Z / bed subsystem keeps its verified geometry
XBEAM_SQ  = 20.0         # 2020 extrusion
XBEAM_LEN = 470.0
MGN12_RAIL_Y0, MGN12_RAIL_Y1 = -18.0, -10.0   # rail body, beam-relative
MGN12_RAIL_ZH = 6.0                            # rail half-height in Z
MGN12_BLOCK_L, MGN12_BLOCK_W, MGN12_BLOCK_H = 45.0, 27.0, 13.0
# MEASURED off the assembly: the part that bolts to the MGN12 block has 4x M3
# bores (r=1.50) with Y axes at x=+-10 and z=40.91/60.91 - a 20 x 20 mm square
# centred exactly on the beam axis. That is the standard MGN12 block pattern.
MGN12_BOLT = 20.0
# MGN12 total height (rail + block) is 13 mm, so with the rail on the
# extrusion's front face at Y -18..-10 the BLOCK MOUNTING FACE is at Y = -23.
MGN12_FACE_Y = -23.0
# My X carriage REPLACES the stock Voron X carriage - it cannot be a spacer
# between block and Voron carriage, because that carriage wraps the block and
# nothing fits between them. So my part takes the block screws and presents
# the toolhead pattern itself.
# MEASURED off the assembly: 4x M3 with Y axes at x=+-16.3 and, relative to
# the beam axis, z = -31.61 and +19.99.
SB_MOUNT_X  = 32.60
SB_MOUNT_Z0 = -31.61
SB_MOUNT_Z1 =  19.99
LM12_OD, LM12_L = 21.0, 30.0
LM10_OD, LM10_L = 19.0, 29.0
XC_LEN  = 58.0            # X carriage length along X
YC_LEN  = 96.0            # Y carriage length along Y

# -------------------------------------------------------------------- belts
PULLEY_PR = 20 * 2.0 / math.pi / 2.0     # GT2 20T pitch radius = 6.366
PULLEY_FL = 16.0
PULLEY_H  = 16.0
BELT_W, BELT_T = 6.0, 1.4
BELT_SIDE_X  = 205.0     # both belt Y-runs (separated in Z)
PULLEY_Y     = 230.0     # rear pulley / idler centreline
# Both belt runs share this Y (no yaw couple) and sit BEHIND the beam: the
# toolhead occupies everything forward of beam-18, so behind is the free side.
BELT_BEAM_Y  = 25.0
BELT_Z_A     = 592.0     # upper belt plane (+-40 from the beam: the wider
                         # separation keeps the carriage yoke above the bed top)
BELT_Z_B     = 526.0     # lower belt plane  (mean = XBEAM_Z = 559)

# --------------------------------------------------------------- NEMA 17 etc
N17_SQ, N17_LEN    = 42.3, 48.0
N17_BOLT, N17_BOSS = 31.0, 22.0
N17_SHAFT_D, N17_SHAFT_L = 5.0, 24.0

# ----------------------------------------------------------------- toolhead
# Nozzle below the beam axis. No longer a guess: MEASURED off the official
# Stealthburner CW2.5 assembly (see the SB_ block below).
TOOL_DROP = 50.91

# Omron TL-W5MC1 inductive bed probe: ferrous target only, 10-30 VDC, NPN-NO
PROBE_L, PROBE_W, PROBE_H = 30.5, 18.0, 10.0
PROBE_BOLT_PITCH = 20.0   # 2x M4; the mount uses slots so pitch is forgiving
PROBE_SENSE    = 5.0
PROBE_STANDOFF = 2.0      # probe face above the sheet at trigger

PRINT_ENV = (245.0, 245.0, 245.0)   # QIDI Q1 Pro - max printable part

# ------------------------------------------------- nozzle wipe / purge dump
# The only place the nozzle can reach outside the print area is the FRONT. The
# rear is out: the Y carriage runs into the A/B motors 7.8 mm past the print
# area. At the front there is 32 mm of overtravel, and two constraints squeeze
# it to a 10 mm window:
#   * the toolhead sticks out 39.6 mm AHEAD of the nozzle, and the front frame
#     members cross x=0 at y=-266, so the nozzle cannot go below -226.4
#   * the brush must clear the bed's sweep (bed front edge -207.1)
# => WIPE_Y must sit in -226.4 .. -216.1.
#
# Purge needs no chute: the column straight down from there is completely
# clear of the bed, the cross rails and the bed mounts, so blobs drop to a bin
# on the table inside the frame's front-left.
WIPE_X = -100.0          # brush centre in X
WIPE_Y = -221.0          # wipe / purge line in Y
PURGE_X = -150.0         # purge beside the brush, so one +X sweep wipes after
BRUSH_L, BRUSH_W = 42.0, 12.0   # pocket for a brass brush strip
BRUSH_FLOOR = 497.0     # brush base sits here; 11.1 mm below the nozzle, so a
                        # 12 mm bristle stands into the nozzle by ~4 mm
WIPE_TOP = 501.0        # bracket top - must stay BELOW the nozzle, because the
                        # gantry does not lift (Z is the bed)
BIN_X, BIN_Y = 100.0, 45.0   # catch-bin footprint under the station

# --------------------------------------------------------------- fasteners
M3, M4, M5 = 3.3, 4.3, 5.3
M3_HEAD, M4_HEAD, M5_HEAD = 6.2, 8.2, 10.2
M3_NUT_AF, M4_NUT_AF, M5_NUT_AF = 5.6, 7.1, 8.1
# 4.5 mm is ~11 perimeters at 0.4 mm - plenty of hoop strength for a pinch
# clamp, and it shrinks every sleeve annulus in the machine by 21%.
CLAMP_WALL = 4.5
SLOT_W     = 2.2

# Sleeve lengths. These could come down once the frame was TRIANGULATED: with
# diagonals carrying the shear, a corner joint no longer has to be moment-stiff,
# it only locates the tubes and carries axial load. The collar does that on
# FRICTION - one M4 at 2.5 N.m gives ~3.1 kN of preload and so ~1.9 kN of axial
# grip at mu=0.3, against member loads of tens of newtons. The closed butt is a
# useful extra compression path and removes 2 mm of slop, but it is not what
# makes the short collar work.
CL_POST = 38.0     # clamp around a post (pass-through)
CL_RAIL = 26.0     # collar on a butted rail end
CL_GUS  = 28.0     # brace gusset clamps
CL_ZMOUNT = 32.0   # Z motor mount rail clamps - shorter than CL_POST so they
                   # stay inboard of the cross-rail end collar
CL_COLLAR = 20.0   # cross-rail END collar - shortened from CL_RAIL so the Z
                   # motor mount can move outboard far enough to clear the
                   # toolhead at full X travel

# ======================================================= derived quantities
NOZZLE_Z      = XBEAM_Z - TOOL_DROP
BED_SURF_HIGH = NOZZLE_Z
BED_SURF_LOW  = BED_SURF_HIGH - BUILD_Z
NUT_HIGH      = BED_SURF_HIGH - BED_RISE
NUT_LOW       = NUT_HIGH - BUILD_Z
BED_PLATE_TOP = BED_SURF_HIGH - BED_STACK
BED_PLATE_BOT = BED_PLATE_TOP - BED_PLATE_T

PR = PULLEY_PR
PULX = BELT_SIDE_X - PR          # 208.634 - rear pulley / idler X magnitude
BELT_REAR_Y = PULLEY_Y + PR      # 236.366 - both belt rear runs
BELT_TURN_Y = BELT_BEAM_Y + PR   #  26.366 - Y-carriage turn-idler centreline

# Each rear corner is ONE coaxial station, and each Y carriage carries ONE
# coaxial idler stud - both belts turn at the same (X,Y), stacked in Z. That is
# how a real CoreXY is arranged, and it is what keeps the corners buildable.
A_MOTOR = (-PULX, PULLEY_Y, BELT_Z_A)   # rear-left,  shaft DOWN, body ABOVE
B_IDLER = (-PULX, PULLEY_Y, BELT_Z_B)   # rear-left,  under the A motor
B_MOTOR = ( PULX, PULLEY_Y, BELT_Z_B)   # rear-right, shaft UP,   body BELOW
A_IDLER = ( PULX, PULLEY_Y, BELT_Z_A)   # rear-right, over the B motor

YC_IDLER_L = (-PULX, BELT_TURN_Y)       # one stud per side, two idlers on it
YC_IDLER_R = ( PULX, BELT_TURN_Y)

A_BODY_BOT = BELT_Z_A + PULLEY_H / 2.0 + 6.0      # 659 -> body 659..707
A_BODY_TOP = A_BODY_BOT + N17_LEN
B_BODY_TOP = BELT_Z_B - PULLEY_H / 2.0 - 6.0      # 577 -> body 529..577
B_BODY_BOT = B_BODY_TOP - N17_LEN

# Y carriage structural envelope
YC_Z0 = BELT_Z_B - PULLEY_H / 2.0 - 13.0          # 570 underside of belt-B fork
YC_Z1 = YROD_Z + LM12_OD / 2.0 + CLAMP_WALL       # 694 top of LM12UU housing
YC_WEB_X1 = POST_X - EMT_OD / 2.0 - 4.0           # 232 must clear the side rail
YC_X1 = YROD_X + LM12_OD / 2.0 + CLAMP_WALL       # 264 outboard edge
YC_Y_MAX = BUILD_Y / 2.0 + YC_LEN / 2.0           # 198 max Y footprint

# Rear-corner post real estate. Six printed parts clamp each rear post, so the
# bands must not overlap: TeeZTop 477..523, Joint4_gan 537..583,
# CornerTower 589..649, YRodBlock 656..700, Joint4_cap 707..753.
TOWER_CLAMP_Z = 560.0
TOWER_CLAMP_L = 60.0
TOWER_SPINE_Z0 = 530.0
TOWER_SPINE_Z1 = 590.0   # stop below the YRodBlock post clamp at 611

# ------------------------------------------------- Voron Stealthburner / CW2
# The toolhead is a stock Voron Stealthburner + Clockwork 2. We do NOT remodel
# it: it is GPLv3, proven, and carries its own part cooling. Instead the
# XCarriage becomes an ADAPTER presenting the Voron X-carriage interface -
# 4x M3, which is what every community adapter does - and the genuine Voron
# parts bolt to it.
#
# !!! THE FOUR VALUES BELOW ARE ASSUMED PLACEHOLDERS, NOT MEASURED. !!!
# I could not find them in any authoritative source and will not invent them
# silently. Measure them off the Stealthburner/CW2 STLs (or the Voron CAD) and
# correct them here; check() below turns a wrong value into a loud failure
# rather than a quietly wrong machine.
# MEASURED from the official CAD: VoronDesign/Voron-Stealthburner,
# CAD/Stealthburner_CW2.5_Assembly.step, imported with ImportGui (the non-GUI
# Import.insert access-violates on these files) and measured in FreeCAD.
# The assembly is posed with the NOZZLE TIP AT THE ORIGIN, and it ships with
# gantry context: a 2020 extrusion at Y 42.10..62.10 / Z 40.91..60.91 and an
# MGN12 rail at Y 34.10..42.10 / Z 44.91..56.91.
#
#   nozzle tip                      Z   0.00  (the datum)
#   MGN12 rail / extrusion centre   Z  50.91  -> nozzle is 50.91 BELOW it
#   toolhead top                    Z 158.23  -> 107.3 ABOVE the rail centre
#   rail front face (mounting)      Y  34.10  -> nozzle 33.9 FORWARD of it
#   width by height:  Z 0..30   76.43 mm  (widest, the duct/LED region)
#                     Z 30..70  71.07 mm
#                     Z 70..138 68.5-69.0 mm
#                     Z 138..158 39.60 mm
#   envelope forward of the rail:  Y -39.60..34.10, X -40.90..35.53
SB_W, SB_D = 76.43, 73.70   # MEASURED max width, and depth forward of the rail
SB_NOZZLE_BELOW_RAIL = 50.91    # MEASURED
SB_NOZZLE_FWD_OF_FACE = 33.90   # MEASURED
SB_TOP_ABOVE_RAIL = 107.32      # MEASURED
SB_ASSUMED = False
SB_BOLT_X  = 40.0    # still assumed; not needed until the mount is settled
SB_BOLT_Z  = 40.0
SB_NOZZLE_BELOW_BOLTS = SB_NOZZLE_BELOW_RAIL   # measured, drives TOOL_DROP
SB_PLATE_T = 8.0                # my adapter plate thickness
SB_FACE_Y  = -34.0              # adapter front face (Voron carriage bolts here)

# ----------------------------------------------------------- toolhead stack
# Superseded by the Stealthburner block above - kept only because the probe
# mount still references PROBE_*; the EXT_* values are no longer used.
EXT_Y          = 0.0      # column on centre: the nozzle has no Y offset
EXT_BODY_YH    = 17.0     # column half-thickness in Y
EXT_BODY_Z0    = 598.0
EXT_BODY_Z1    = 630.0
EXT_MOTOR_FACE = 652.0    # above belt A, so the shaft never crosses a belt
HOTEND_Z1      = 598.0
BELT_TOWER_Y0  = 14.0     # carriage belt clamp towers, clear of the pocket
BELT_TOWER_Y1  = 26.0

XC_HALF = XC_LEN / 2.0
X_TRAVEL_LIM = (BELT_SIDE_X - 2 * PR) - XC_HALF
Y_TRAVEL_LIM = (YROD_LEN / 2.0 - 20.0) - YC_LEN / 2.0

N17H = N17_SQ / 2.0
RAIL_IN_Y = POST_Y - EMT_OD / 2.0      # inner face of the Y=+-POST_Y rails
RAIL_IN_X = POST_X - EMT_OD / 2.0

# Genuine ONE-DIMENSIONAL invariants only. Everything that is really a
# body-vs-body question lives in collide.py, which tests true 3D overlap over
# sampled machine poses - a per-axis "clearance" wrongly fails any pair that
# overlaps in one axis while being safely separated in another.
CLEARANCES = {
 "X travel margin (need +-150)":
    X_TRAVEL_LIM - BUILD_X / 2.0,
 "Y travel margin (need +-150)":
    Y_TRAVEL_LIM - BUILD_Y / 2.0,
 "screw top -> nut at top of travel":
    (ZSCREW_Z0 + ZSCREW_LEN) - NUT_HIGH,
 "nut at bottom -> screw bottom":
    NUT_LOW - ZSCREW_Z0,
 "Z motor body -> floor":
    (ZMOT_FACE - N17_LEN) - Z_FOOT,
 "Z motor shaft top -> screw bottom (coupler gap)":
    ZSCREW_Z0 - (ZMOT_FACE + N17_SHAFT_L),
}


def check():
    """Every clearance must be positive, plus the invariants."""
    e = ["%s = %+.2f mm" % (k, v) for k, v in CLEARANCES.items() if v <= 0]
    if abs(NOZZLE_Z - BED_SURF_HIGH) > 1e-9:
        e.append("nozzle Z %.1f != bed surface top of travel %.1f"
                 % (NOZZLE_Z, BED_SURF_HIGH))
    if abs((BELT_Z_A + BELT_Z_B) / 2.0 - XBEAM_Z) > 0.01:
        e.append("belt planes not centred on the X beam")
    # Stealthburner must land the nozzle exactly where the Z stack expects it
    if abs(SB_NOZZLE_BELOW_BOLTS - TOOL_DROP) > 0.01:
        e.append("Stealthburner nozzle sits %.1f mm below the rod axis but "
                 "TOOL_DROP is %.1f - set TOOL_DROP to match and re-run, which "
                 "moves the whole Z stack"
                 % (SB_NOZZLE_BELOW_BOLTS, TOOL_DROP))
    # a wide toolhead hits the Z rods before it runs out of X travel
    if SB_W / 2.0 + BUILD_X / 2.0 > ZROD_X - ZROD_D / 2.0:
        e.append("Stealthburner is %.0f mm wide, so at +-%.0f of X travel it "
                 "reaches %.0f and the Z rods are at %.0f - move ZROD_X out or "
                 "cut X travel" % (SB_W, BUILD_X / 2.0,
                                   SB_W / 2.0 + BUILD_X / 2.0,
                                   ZROD_X - ZROD_D / 2.0))
    if ZROD_Z0 > NUT_LOW - LM10_L / 2.0 or ZROD_Z0 + ZROD_LEN < NUT_HIGH + LM10_L / 2.0:
        e.append("Z rods %.0f..%.0f miss bearing sweep %.0f..%.0f"
                 % (ZROD_Z0, ZROD_Z0 + ZROD_LEN,
                    NUT_LOW - LM10_L / 2.0, NUT_HIGH + LM10_L / 2.0))
    # Every wheel must be exactly PR from both straight runs it joins, or the
    # belt does not actually lie on the path the model draws.
    for nm, (x, y, z) in (("A_MOTOR", A_MOTOR), ("A_IDLER", A_IDLER),
                          ("B_MOTOR", B_MOTOR), ("B_IDLER", B_IDLER)):
        if abs(abs(x) + PR - BELT_SIDE_X) > 1e-9:
            e.append("%s not tangent to the side run" % nm)
        if abs(y + PR - BELT_REAR_Y) > 1e-9:
            e.append("%s not tangent to the rear run" % nm)
    # nozzle wipe station must be reachable and clear of the bed
    _nz_front = -(YROD_LEN / 2.0 - 20.0 - YC_LEN / 2.0) + BED_Y
    if WIPE_Y - 39.60 < -POST_Y + EMT_OD / 2.0:
        e.append("wipe station at Y=%.1f puts the toolhead nose at %.1f, into "
                 "the front frame at %.1f" % (WIPE_Y, WIPE_Y - 39.60,
                                              -POST_Y + EMT_OD / 2.0))
    if WIPE_Y < _nz_front:
        e.append("nozzle cannot reach Y=%.1f (front limit %.1f)"
                 % (WIPE_Y, _nz_front))
    for nm, x in (("WIPE_X", WIPE_X), ("PURGE_X", PURGE_X)):
        if abs(x) > X_TRAVEL_LIM:
            e.append("nozzle cannot reach %s=%.1f (X limit +-%.1f)"
                     % (nm, x, X_TRAVEL_LIM))
    if abs(PURGE_X - WIPE_X) < BRUSH_L / 2.0 + 26.0:
        e.append("purge at X=%.1f lands on the wipe bracket (brush at %.1f)"
                 % (PURGE_X, WIPE_X))
    if BRUSH_FLOOR >= NOZZLE_Z or BRUSH_FLOOR + 14.0 < NOZZLE_Z:
        e.append("brush floor %.1f gives no sane bristle reach to the nozzle "
                 "at %.1f" % (BRUSH_FLOOR, NOZZLE_Z))
    if WIPE_Y + BRUSH_W / 2.0 > BED_Y - BED_PLATE / 2.0 - 3.0:
        e.append("brush at Y=%.1f fouls the bed sweep (bed front edge %.1f)"
                 % (WIPE_Y, BED_Y - BED_PLATE / 2.0))
    if WIPE_TOP >= NOZZLE_Z:
        e.append("wipe bracket top %.1f is at or above the nozzle %.1f"
                 % (WIPE_TOP, NOZZLE_Z))
    for nm, (x, y) in (("YC_IDLER_L", YC_IDLER_L), ("YC_IDLER_R", YC_IDLER_R)):
        if abs(abs(x) + PR - BELT_SIDE_X) > 1e-9:
            e.append("%s not tangent to the side run" % nm)
        if abs(y - PR - BELT_BEAM_Y) > 1e-9:
            e.append("%s not tangent to the beam run" % nm)
    return e


def belt_path(plane):
    """The closed rectangle a belt traces, as (x,y) corner-to-corner runs.
    Used by the model and by the tangency check above."""
    S, RY, BY, TY = BELT_SIDE_X, BELT_REAR_Y, BELT_BEAM_Y, BELT_TURN_Y
    if plane == "A":
        return [((-PULX, BY), (PULX, BY)), ((-S, TY), (-S, PULLEY_Y)),
                ((-PULX, RY), (PULX, RY)), ((S, PULLEY_Y), (S, TY))]
    return [((-PULX, BY), (PULX, BY)), ((S, TY), (S, PULLEY_Y)),
            ((PULX, RY), (-PULX, RY)), ((-S, PULLEY_Y), (-S, TY))]


def braces():
    """Each entry: name, endpoints, brace-plane normal, and the two ANCHORS
    (a point on the anchored tube axis plus that tube's direction) that the end
    gussets clamp onto.

    Note what is NOT here: a diagonal in the side planes above the gantry. The
    Y carriages sweep X 232..264 at Z 662..694 in exactly those planes, so no
    brace can live there. Torsional stiffness up top has to come from a bolted
    side PANEL instead - which is the enclosure anyway.
    """
    out = []
    yn, xn = POST_Y - BRACE_NODE, POST_X - BRACE_NODE
    for sx in (-1, 1):
        X = sx * POST_X
        out.append(dict(
            name="Brace_side_%s" % ("p" if sx > 0 else "m"),
            p0=(X, yn, SIDE_BR_Z0), p1=(X, -yn, SIDE_BR_Z1), n=(1, 0, 0),
            a0=((X, POST_Y, 0.0), (0, 0, 1)),
            a1=((X, -POST_Y, 0.0), (0, 0, 1))))
    # Rear lower brace anchors to the RAILS, not the posts: both side braces
    # already end on the rear posts and the gussets would fight for the space.
    # Rail-to-rail also means it spans the full base height in one member.
    out.append(dict(
        name="Brace_rear", p0=(-REAR_UP_X, POST_Y + BRACE_OFF, Z_BOT),
        p1=(REAR_UP_X, POST_Y + BRACE_OFF, Z_CAP), n=(0, 1, 0),
        a0=((0.0, POST_Y, Z_BOT), (1, 0, 0)),
        a1=((0.0, POST_Y, Z_CAP), (1, 0, 0))))
    # rear upper diagonal: rail-to-rail, because every band on the rear posts
    # up here is already taken. This is the one that reacts the gantry loads.
    # Rail-anchored braces are offset one tube diameter OUT of the rail plane,
    # or the brace axis would run straight through the rail it anchors to; the
    # end gusset bridges that offset.
    # cap plane: two opposite corner braces triangulate the top rectangle in
    # plan, anchored mid-span on the rails where there is room
    for sx, sy in ((-1, -1), (1, 1)):
        tag = ("p" if sx > 0 else "m") + ("p" if sy > 0 else "m")
        out.append(dict(
            name="Brace_cap_%s" % tag,
            p0=(sx * CAP_BR_A, sy * POST_Y, Z_CAP + BRACE_OFF),
            p1=(sx * POST_X, sy * CAP_BR_A, Z_CAP + BRACE_OFF), n=(0, 0, 1),
            a0=((0.0, sy * POST_Y, Z_CAP), (1, 0, 0)),
            a1=((sx * POST_X, 0.0, Z_CAP), (0, 1, 0))))
    return out


def brace_len(p0, p1):
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(p0, p1)))


def klipper_xy(x, y):
    """Model mm -> Klipper mm. Klipper's origin is the front-left corner of the
    PRINT AREA, not the machine centre, and the whole bed sits forward by
    BED_Y, so neither offset is BUILD/2 on its own."""
    return x + BUILD_X / 2.0, y - (BED_Y - BUILD_Y / 2.0)


def cutlist():
    rows = [("post", 4, POST_LEN),
            ("rail along X: bottom x2, cap x2, front mid, front wipe, "
             "2 Z-motor cross", 8, RAIL_X_LEN),
            ("rail along Y: bottom x2, cap x2", 4, RAIL_Y_LEN)]
    for b in braces():
        rows.append((b["name"].replace("_", " "), 1,
                     brace_len(b["p0"], b["p1"])))
    return rows


# ===========================================================================
# THE REAR POST SQUEEZE - the open problem blocking the MGN12 conversion
# ===========================================================================
# Measuring the real Stealthburner halved the nozzle-to-beam distance, from a
# guessed 110 mm to a measured 50.91. That compresses the whole vertical stack,
# and the rear posts end up over-subscribed. Each rear post must carry, in
# non-overlapping Z bands: the Z-top rail tee (TeeZTop), the rear corner tower,
# the Y-rod end block, and the cap corner joint - and the tower's B-motor plate
# has to reach Y=245.5 for its bolts while TeeZTop's Y-socket starts at 239.5.
# Those two cannot both exist. Shuffling PULLEY_Y does not help: the motor body
# must stay behind the Y-carriage sweep (>= 203) yet in front of the socket
# (<= 216.5).
#
# RESOLVED by dropping the Z-rod top support entirely: the Z_ZTOP rails and
# the ZRodTop brackets are gone and the rods cantilever from their feet. That
# freed the whole 496..534 band, left the rear post with only tower +
# YRodBlock + Joint4_cap, and deleted 2 rails, 4x TeeZTop and 2x ZRodTop.
# The tradeoff is real and worth a decision: 10 mm rods cantilevered ~480 mm.
# The screws carry the bed's weight, so the rods only resist pitch and yaw -
# plenty of printers run unsupported Z rods - but it is less rigid than a
# top-supported pair.
