# -*- coding: utf-8 -*-
"""EMT CoreXY - gantry, belts and toolhead stages."""
import math
import FreeCAD as App
import Part
from FreeCAD import Vector as V

import params as P
from geom import (doc, put, clear, bx, cz, cx, cyl_y, xform, Pt, clamp,
                  emt, nema17, pulley, belt_run, PRINTED,
                  STEEL, ROD, BRASS, PRINTP, MOTOR, BELTC, BEDC)
from stages import mir_x, mir_y, rotz, trz, SGN, K, E

PULX = P.PULX
PY = P.PULLEY_Y
TY = P.BELT_TURN_Y


# ===================================================== gantry hardware
def stage_gantry_hardware():
    g = "C1_Gantry_Hardware"
    BH = P.XBEAM_SQ / 2.0
    for sx in SGN:
        put("YRod_%s" % K[sx],
            cyl_y(sx * P.YROD_X, P.YROD_Z, -P.YROD_LEN / 2.0, P.YROD_LEN / 2.0,
                  P.YROD_D), ROD, g)
    # X axis: 2020 extrusion with the MGN12 rail on its FRONT face, and the
    # block. Cross-section taken straight off the measured Voron assembly.
    put("XBeam_2020", bx(-P.XBEAM_LEN / 2.0, P.XBEAM_LEN / 2.0, -BH, BH,
                         P.XBEAM_Z - BH, P.XBEAM_Z + BH), (0.62, 0.64, 0.66), g)
    put("MGN12_Rail", bx(-P.XBEAM_LEN / 2.0, P.XBEAM_LEN / 2.0,
                         P.MGN12_RAIL_Y0, P.MGN12_RAIL_Y1,
                         P.XBEAM_Z - P.MGN12_RAIL_ZH,
                         P.XBEAM_Z + P.MGN12_RAIL_ZH), STEEL, g)
    put("MGN12_Block", bx(-P.MGN12_BLOCK_L / 2.0, P.MGN12_BLOCK_L / 2.0,
                          P.MGN12_FACE_Y, P.MGN12_RAIL_Y1,
                          P.XBEAM_Z - P.MGN12_BLOCK_W / 2.0,
                          P.XBEAM_Z + P.MGN12_BLOCK_W / 2.0), MOTOR, g)
    put("MotorA", nema17((-PULX, PY), P.A_BODY_BOT, -1), MOTOR, g)
    put("PulleyA", pulley(-PULX, PY, P.BELT_Z_A), MOTOR, g)
    put("IdlerB_rear", pulley(-PULX, PY, P.BELT_Z_B), MOTOR, g)
    put("MotorB", nema17((PULX, PY), P.B_BODY_TOP, +1), MOTOR, g)
    put("PulleyB", pulley(PULX, PY, P.BELT_Z_B), MOTOR, g)
    put("IdlerA_rear", pulley(PULX, PY, P.BELT_Z_A), MOTOR, g)
    for sx in SGN:
        put("YC_IdlerA_%s" % K[sx], pulley(sx * PULX, TY, P.BELT_Z_A), MOTOR, g)
        put("YC_IdlerB_%s" % K[sx], pulley(sx * PULX, TY, P.BELT_Z_B), MOTOR, g)
    gb = "C2_Belts"
    for plane, z in (("A", P.BELT_Z_A), ("B", P.BELT_Z_B)):
        for i, (a, b) in enumerate(P.belt_path(plane)):
            put("Belt%s_%d" % (plane, i), belt_run(a, b, z), BELTC, gb)
    return True


# ===================================================== Y rod end block
def yrod_block_shape():
    """Clamps a POST at the Y-rod height and carries the Y rod end. Clamping
    the post rather than a rail keeps it out of the rear corner tower."""
    x, y, z = P.POST_X, P.POST_Y, P.YROD_Z
    rod_end = P.YROD_LEN / 2.0
    p = Pt("YRodBlock")
    b, c, h = clamp("z", (x, y, z), P.CL_POST, slot_deg=45.0)
    p.add(b).sub(*c)
    p.add(cyl_y(P.YROD_X, z, 246.0, y - 10.0, P.YROD_D + 2 * P.CLAMP_WALL))
    p.add(bx(P.YROD_X - 11, x + 8, 246.0, y - 10.0, z - 11, z + 11))
    p.sub(cyl_y(P.YROD_X, z, 245.0, rod_end + 1.5, P.YROD_D + 0.15))
    p.sub(bx(P.YROD_X - 1.1, P.YROD_X + 1.1, 247.0, rod_end + 1.0, z, z + 13))
    p.sub(cx(rod_end - 7.0, z + 6.5, P.YROD_X - 13, P.YROD_X + 13, P.M4))
    return p.build(qty=4, note="Y rod end blocks (2 mirrored pairs)")


# ===================================================== Y carriage
def y_carriage_shape():
    """+X side, parked at Y=0. Rides the Y rod on 2x LM12UU, CLAMPS THE 2020
    EXTRUSION END (the X axis is now a rail on an extrusion, not two rods), and
    carries this side's coaxial idler stud on open forks."""
    BH = P.XBEAM_SQ / 2.0
    e1 = P.XBEAM_LEN / 2.0
    e0 = e1 - 24.0
    p = Pt("YCarriage")
    b, c, h = clamp("y", (P.YROD_X, 0.0, P.YROD_Z), P.YC_LEN,
                    slot_deg=-90.0, bore=P.LM12_OD)
    p.add(b).sub(*c)
    # extrusion end clamp. Its Z span is raised clear of the gantry side rail
    # (551..569) - it overlaps that rail in X, so Z is what separates them.
    p.add(bx(e0 - 4, e1 + 4, -BH - 7, BH + 7,
             P.XBEAM_Z - BH - 8, P.XBEAM_Z + BH + 8))
    p.sub(bx(e0 - 5, e1 + 5, -BH - 0.15, BH + 0.15,
             P.XBEAM_Z - BH - 0.15, P.XBEAM_Z + BH + 0.15))
    # relief for the MGN12 rail, which runs the full length of the beam and so
    # passes straight through this clamp
    p.sub(bx(e0 - 5, e1 + 5, P.MGN12_RAIL_Y0 - 0.15, P.MGN12_RAIL_Y1 + 0.25,
             P.XBEAM_Z - P.MGN12_RAIL_ZH - 0.15,
             P.XBEAM_Z + P.MGN12_RAIL_ZH + 0.15))
    p.sub(bx(e0 - 5, e1 + 5, -1.1, 1.1, P.XBEAM_Z + BH, P.XBEAM_Z + BH + 9))
    p.sub(cx(0.0, P.XBEAM_Z + BH + 4.0, e0 + 2, e0 + 20, P.M4))
    # web out to the bearing housing
    p.add(bx(e1 - 8, 250.0, -40, 40, P.XBEAM_Z + 8, P.YROD_Z - 2))
    # lightening pocket, kept OUTBOARD of the extrusion clamp: taken any
    # further inboard it removes the only material bridging the clamp to the
    # rest of the carriage and the part falls into two solids.
    p.sub(bx(234.0, 252.0, -20, 20, P.XBEAM_Z + 14, P.YROD_Z - 4))
    # idler spine, kept clear of the belt side runs at x=BELT_SIDE_X
    # spine reaches back to TY-21 so it actually overlaps the extrusion clamp
    # (which ends at y=+17); at TY-14 the overlap was 0.37 mm and the part
    # fell into two solids
    p.add(bx(208.0, 219.0, TY - 21, TY + 14, P.BELT_Z_B - 17, P.BELT_Z_A + 13))
    for z in (P.BELT_Z_A, P.BELT_Z_B):
        p.add(bx(190.0, 214.0, TY - 13, TY + 13, z - 11, z - 7))
        p.add(bx(190.0, 214.0, TY - 13, TY + 13, z + 7, z + 11))
    p.sub(cz(PULX, TY, P.BELT_Z_B - 19, P.BELT_Z_A + 15, P.M5))
    return p.build(qty=2, note="Y carriage, one per side (mirrored pair)")


# ===================================================== X carriage
def x_carriage_shape():
    """Bolts to the MGN12 block and carries BOTH the belt clamps and the
    toolhead. It REPLACES the stock Voron X carriage rather than spacing it off
    the block - that carriage wraps the block, so nothing fits between them.

    Both bolt patterns are measured off the official assembly: 4x M3 on a
    20 x 20 square to the block, and 4x M3 at x=+-16.3 / z -31.61,+19.99 for
    the toolhead. The yokes pass OVER and UNDER the extrusion to reach the
    belt clamps behind it.
    """
    zc = P.XBEAM_Z
    fy = P.MGN12_FACE_Y
    p = Pt("XCarriage")
    p.add(bx(-P.XC_HALF, P.XC_HALF, fy - 8.0, fy,
             P.BELT_Z_B - 13, P.BELT_Z_A + 13))
    for sx in SGN:
        for sz in SGN:
            p.sub(cyl_y(sx * P.MGN12_BOLT / 2.0, zc + sz * P.MGN12_BOLT / 2.0,
                        fy - 9.0, fy + 6.0, P.M3))
    for sx in SGN:
        for z in (zc + P.SB_MOUNT_Z0, zc + P.SB_MOUNT_Z1):
            p.sub(cyl_y(sx * P.SB_MOUNT_X / 2.0, z, fy - 9.0, fy + 1.0, P.M3))
    for z0, z1, bz in ((P.BELT_Z_A - 12, P.BELT_Z_A + 13, P.BELT_Z_A),
                       (P.BELT_Z_B - 13, P.BELT_Z_B + 12, P.BELT_Z_B)):
        p.add(bx(-P.XC_HALF, P.XC_HALF, fy - 8.0, P.BELT_BEAM_Y + 8.0, z0, z1))
        p.sub(bx(-P.XC_HALF - 1, P.XC_HALF + 1,
                 P.BELT_BEAM_Y - 1.0, P.BELT_BEAM_Y + 1.0,
                 bz - P.BELT_W / 2.0 - 0.3, bz + P.BELT_W / 2.0 + 0.3))
        for sx in SGN:
            p.sub(cz(sx * 20.0, P.BELT_BEAM_Y, z0 - 1, z1 + 1, P.M3))
    return p.build(qty=1, note="X carriage: MGN12 block -> belts + toolhead")


# ===================================================== rear corner towers
def corner_tower_shape(upper_is_motor):
    """One per rear corner. Carries a motor and the OTHER belt's idler on one
    coaxial station at (PULX, PULLEY_Y).

    Post real estate drives the shape. The post is already clamped by
    Joint4_gan (537..583, whose 45 deg pinch lug reaches Y=254.2, and whose
    gantry Y-socket reaches Z=574.7) and by YRodBlock (656..700, web at
    Y 246..265 / Z 667..689). So:
      * the MAIN BODY may be full depth in Y, but only inside the free band
        589..649, which is where this part clamps the post;
      * the two LEGS that reach out of that band to the motor plates must stay
        at Y <= 250 to pass those neighbours.
    """
    x, y = P.POST_X, P.POST_Y
    p = Pt("CornerTower_%s" % ("Aup" if upper_is_motor else "Bup"))
    b, c, h = clamp("z", (x, y, P.TOWER_CLAMP_Z), P.TOWER_CLAMP_L, slot_deg=45.0)
    p.add(b).sub(*c)
    # main body: full Y depth, confined to the free post band
    p.add(bx(x - 16, x + 14, PY - 16, y + 14,
             P.TOWER_CLAMP_Z - P.TOWER_CLAMP_L / 2.0,
             P.TOWER_CLAMP_Z + P.TOWER_CLAMP_L / 2.0))
    # legs out of the band, kept inboard of the neighbouring clamps
    p.add(bx(x - 16, x + 14, PY - 16, 250.0, P.B_BODY_TOP, P.TOWER_SPINE_Z0))
    p.add(bx(x - 16, x + 14, PY - 16, 250.0,
                 P.TOWER_SPINE_Z1, P.BELT_Z_A + 19.0))
    if upper_is_motor:
        # A motor plate on top: motor sits above it, shaft down through the bore
        p.add(bx(PULX - 26, x + 10, PY - 23, 250.0,
                 P.A_BODY_BOT - 8, P.A_BODY_BOT))
        p.sub(cz(PULX, PY, P.A_BODY_BOT - 9, P.A_BODY_BOT + 1, 28.0))
        for sa in SGN:
            for sb in SGN:
                p.sub(cz(PULX + sa * P.N17_BOLT / 2.0,
                         PY + sb * P.N17_BOLT / 2.0,
                         P.A_BODY_BOT - 9, P.A_BODY_BOT + 1, P.M3))
        # lower wheel is the belt-B idler on a stud
        p.add(bx(PULX - 16, x + 10, PY - 16, 244.0,
                 P.BELT_Z_B - 15, P.BELT_Z_B - 5))
        p.sub(cz(PULX, PY, P.BELT_Z_B - 17, P.BELT_Z_B - 4, P.M5))
    else:
        # B motor plate below: motor hangs under it, shaft up through the bore.
        # The bore is wider than the pulley flange so the pulley can sit in it.
        p.add(bx(PULX - 26, x + 10, PY - 23, 250.0,
                 P.B_BODY_TOP, P.B_BODY_TOP + 8))
        p.sub(cz(PULX, PY, P.B_BODY_TOP - 1, P.B_BODY_TOP + 9, 23.0))
        for sa in SGN:
            for sb in SGN:
                p.sub(cz(PULX + sa * P.N17_BOLT / 2.0,
                         PY + sb * P.N17_BOLT / 2.0,
                         P.B_BODY_TOP - 1, P.B_BODY_TOP + 9, P.M3))
        # upper wheel is the belt-A idler on a stud
        p.add(bx(PULX - 16, x + 10, PY - 16, 244.0,
                 P.BELT_Z_A + 12, P.BELT_Z_A + 24))
        p.sub(cz(PULX, PY, P.BELT_Z_A + 4, P.BELT_Z_A + 26, P.M5))
    return p.build(qty=1, note="rear corner tower")


def stage_gantry_printed():
    g = "C3_Printed_Gantry"
    yb = yrod_block_shape()
    put("YRodBlock_pp", yb, PRINTP, g)
    put("YRodBlock_pm", mir_y(yb), PRINTP, g)
    put("YRodBlock_mp", mir_x(yb), PRINTP, g)
    put("YRodBlock_mm", mir_x(mir_y(yb)), PRINTP, g)
    yc = y_carriage_shape()
    put("YCarriage_p", yc, PRINTP, g)
    put("YCarriage_m", mir_x(yc), PRINTP, g)
    put("XCarriage", x_carriage_shape(), PRINTP, g)
    # rear-right: B motor low, A idler high. rear-left: mirror of it.
    tr = corner_tower_shape(upper_is_motor=False)
    put("CornerTower_R", tr, PRINTP, g)
    tl = corner_tower_shape(upper_is_motor=True)
    put("CornerTower_L", mir_x(tl), PRINTP, g)
    return True


# ===================================================== toolhead
def stage_toolhead():
    """Stock Voron Stealthburner + Clockwork 2.5 + Rapido, drawn as its
    MEASURED envelope. It hangs forward of the beam: the nozzle sits BED_Y
    ahead of the gantry centre, which is why the bed/Z subsystem is shifted
    forward by the same amount."""
    g = "D1_Toolhead"
    ny = P.BED_Y
    put("Stealthburner", bx(-40.90, 35.53, ny - 39.60, ny + 34.10,
                            P.NOZZLE_Z + 10.0, P.NOZZLE_Z + 158.23),
        (0.30, 0.30, 0.34), g)
    put("Nozzle", cz(0.0, ny, P.NOZZLE_Z, P.NOZZLE_Z + 20.0, 10.0),
        (0.8, 0.7, 0.3), g)
    return True


def probe_mount_shape():
    """Slotted vertically: an inductive sensor trigger distance varies with
    target material and temperature, so the standoff must be trimmable."""
    pz = P.NOZZLE_Z + P.PROBE_STANDOFF
    p = Pt("ProbeMount")
    # The probe hangs from the UNDERSIDE of a top plate. Nothing may sit below
    # the probe face: at the top of Z travel the bed surface is at NOZZLE_Z,
    # and the probe face is only PROBE_STANDOFF above it.
    p.add(bx(-24, 24, -48.0, -27.0, pz + P.PROBE_H, pz + P.PROBE_H + 12.0))
    # riser up the front face of the carriage front plate
    p.add(bx(-24, 24, -34.0, -27.0, pz + P.PROBE_H, 600.0))
    for sx in SGN:
        # vertical slots: trim the standoff after assembly
        p.sub(bx(sx * 20.0 - 2.15, sx * 20.0 + 2.15, -35.0, -26.0,
                 556.0, 594.0))
        p.sub(cz(sx * P.PROBE_BOLT_PITCH / 2.0, -46.0 + P.PROBE_W / 2.0,
                 pz + P.PROBE_H - 1.0, pz + P.PROBE_H + 13.0, P.M4))
    return p.build(qty=1, note="TL-W5MC1 probe mount, height-slotted")
