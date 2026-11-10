# -*- coding: utf-8 -*-
"""EMT CoreXY - build stages. Each stage is one RPC call's worth of booleans.

Symmetric printed parts are built ONCE and mirrored/rotated into place, which
keeps the boolean count per call low (freecad-mcp-heavy-booleans) and
guarantees the instances are genuinely identical parts.
"""
import math
import FreeCAD as App
import Part
from FreeCAD import Vector as V

import params as P
from geom import (doc, put, group, clear, bx, cz, cx, cyl_y, xform, Pt, clamp,
                  clamp_at,
                  emt, nema17, pulley, belt_run, PRINTED,
                  STEEL, ROD, BRASS, PRINTP, MOTOR, BELTC, BEDC)

E = P.EMT_OD / 2.0
RH = P.RAIL_X_LEN / 2.0
RHY = P.RAIL_Y_LEN / 2.0

SGN = (-1, 1)
K = {-1: "m", 1: "p"}


# Mirroring, twice bitten:
#   1. Shape.mirror() RETURNS the mirrored shape and leaves the original
#      untouched, unlike rotate()/translate() which mutate in place. Ignoring
#      the return value silently stacks a part on top of its twin.
#   2. Worse, mirror() DISCARDS the shape's Placement, so mirroring anything
#      that has already been rotated gives a wrong position with no error -
#      mir_y(rotz(s,180)) landed on top of mir_y(s).
# transformShape() applies the matrix in global space, composes correctly with
# a prior rotation, and leaves planes as planes (no NURBS conversion).
def _mirror_matrix(axis):
    m = App.Matrix()
    if axis == "x":
        m.A11 = -1.0
    else:
        m.A22 = -1.0
    return m


def mir_x(s):
    t = s.copy()
    t.transformShape(_mirror_matrix("x"))
    return t


def mir_y(s):
    t = s.copy()
    t.transformShape(_mirror_matrix("y"))
    return t


def rotz(s, deg):
    t = s.copy()
    t.rotate(V(0, 0, 0), V(0, 0, 1), deg)
    return t


def try_(s, dy):
    """Translate in Y. The whole bed / Z subsystem is modelled BED-CENTRED and
    then shifted forward by BED_Y, which keeps every mir_y() placement valid -
    mirroring about y=0 only works before the offset is applied."""
    t = s.copy()
    t.translate(V(0, dy, 0))
    return t


def trz(s, dz):
    t = s.copy()
    t.translate(V(0, 0, dz))
    return t


# =========================================================== stage 1: conduit
def stage_frame():
    g = "A1_Frame_EMT"
    for sx in SGN:
        for sy in SGN:
            put("Post_%s%s" % (K[sx], K[sy]),
                emt((sx * P.POST_X, sy * P.POST_Y, P.Z_FOOT),
                    (sx * P.POST_X, sy * P.POST_Y, P.Z_CAP)), STEEL, g)
    for z, tag in ((P.Z_BOT, "bot"), (P.Z_CAP, "cap")):
        for sy in SGN:
            put("RailX_%s_%s" % (tag, K[sy]),
                emt((-RH, sy * P.POST_Y, z), (RH, sy * P.POST_Y, z)), STEEL, g)
        for sx in SGN:
            put("RailY_%s_%s" % (tag, K[sx]),
                emt((sx * P.POST_X, -RHY, z), (sx * P.POST_X, RHY, z)), STEEL, g)
    # Mid plane: FRONT rail only. The side and rear mid rails are gone - their
    # planes carry diagonals instead, and a mid rail would be in the way.
    put("RailX_mid_m", emt((-RH, -P.POST_Y, P.Z_MID), (RH, -P.POST_Y, P.Z_MID)),
        STEEL, g)
    # front rail carrying the nozzle wipe / purge station. The front post has
    # four occupied clamp bands (Joint4 bot/mid/cap, side-brace gusset, Y-rod
    # block); Z_WIPE sits in the long free stretch between the mid joint and
    # the gusset.
    put("RailX_wipe_m",
        emt((-RH, -P.POST_Y, P.Z_WIPE), (RH, -P.POST_Y, P.Z_WIPE)), STEEL, g)
    for sy in SGN:
        put("RailX_zcross_%s" % K[sy],
            emt((-RH, P.BED_Y + sy * P.ZCROSS_Y, P.Z_BOT),
                (RH, P.BED_Y + sy * P.ZCROSS_Y, P.Z_BOT)), STEEL, g)
    # diagonals - the actual shear bracing
    for b in P.braces():
        put(b["name"], emt(b["p0"], b["p1"]), (0.45, 0.50, 0.55), g)
    return len(doc().Objects)


# ================================================== stage 2: frame joints
#
# IMPORTANT: parts that clamp a post are built with the post axis AT THE
# ORIGIN and then rotated about their own axis and translated to the corner.
# Rotating a part that was built at (POST_X, POST_Y) about the GLOBAL origin
# only lands on another corner if the frame is square - this frame is
# 490 x 550, so a 90 deg global rotation threw two joints per level off the
# posts entirely.
CORNER_ROT = {(1, 1): 0.0, (-1, 1): 90.0, (-1, -1): 180.0, (1, -1): 270.0}


def place_corner(shape, sx, sy, z):
    """Rotate a corner part about its own axis to aim its sockets inboard,
    then translate it onto the (sx, sy) post at height z."""
    t = rotz(shape, CORNER_ROT[(sx, sy)])
    t.translate(V(sx * P.POST_X, sy * P.POST_Y, z))
    return t


def joint4_shape():
    """4-way frame corner, built with the post axis at the origin and its two
    rail sockets pointing -X and -Y (i.e. inboard at the (+X,+Y) corner)."""
    p = Pt("Joint4_corner")
    # post clamp, pinch slot aimed out along the +X+Y diagonal
    b, c, h = clamp("z", (0, 0, 0), P.CL_POST, slot_deg=45.0)
    p.add(b).sub(*c)
    # Rail sockets reaching inboard; the rail end stops EMT_GAP off the post.
    # Pinch lugs point DOWN (slot_deg 0 for X, +90 for Y): aimed up, the
    # gantry-plane socket block reaches z=584.7 and fouls the corner tower.
    d = E + P.EMT_GAP + P.CL_RAIL / 2.0
    bxx, cxx, _ = clamp("x", (-d, 0, 0), P.CL_RAIL, slot_deg=0.0)
    p.add(bxx).sub(*cxx)
    byy, cyy, _ = clamp("y", (0, -d, 0), P.CL_RAIL, slot_deg=90.0)
    p.add(byy).sub(*cyy)
    return p.build(qty=16, note="all 16 frame corners, 4 planes x 4; identical")


def foot_shape():
    """Post end cap + floor pad, built with the post axis at the origin."""
    p = Pt("FootPad")
    b, c, h = clamp("z", (0, 0, 20.0), P.CL_POST, slot_deg=45.0)
    p.add(b).sub(*c)
    p.add(cz(0, 0, -6.0, 4.0, 56.0))
    # blind: plug the bore below the post end so the pad is a real foot
    p.sub(cz(0, 0, 2.0, 60.0, P.EMT_BORE))
    return p.build(qty=4, note="feet")


def tee_zcross_shape():
    """Z-motor cross rail (along X) butting the bottom side rail (along Y)."""
    px, py, z = P.POST_X, P.ZCROSS_Y, 0.0
    p = Pt("TeeZCross")
    b, c, h = clamp("y", (px, py, z), P.CL_POST, slot_deg=-90.0)
    p.add(b).sub(*c)
    # Short collar gripping only the last 24 mm of the cross rail. A full
    # 36 mm socket reaches x=198 and collides with the Z motor mount clamp.
    b2, c2, _ = clamp("x", (P.RAIL_X_LEN / 2.0 - P.CL_COLLAR / 2.0, py, z),
                      P.CL_COLLAR, slot_deg=180.0)
    p.add(b2).sub(*c2)
    return p.build(qty=4, note="bottom cross rails -> side rails")


def tee_ztop_shape():
    """Z-top side rail (along Y) butting a post. Built at the origin with its
    socket pointing -Y, so the +Y posts take it as-is and the -Y posts take it
    rotated 180 deg."""
    p = Pt("TeeZTop")
    b, c, h = clamp("z", (0, 0, 0), P.CL_POST, slot_deg=45.0)
    p.add(b).sub(*c)
    d = E + P.EMT_GAP + 18.0
    b2, c2, _ = clamp("y", (0, -d, 0), 36.0, slot_deg=90.0)
    p.add(b2).sub(*c2)
    return p.build(qty=4, note="Z-top side rails -> posts")


def stage_joints():
    g = "A2_Printed_FrameJoints"
    j = joint4_shape()
    n = 0
    for z, tag in ((P.Z_BOT, "bot"), (P.Z_CAP, "cap")):
        for sx in SGN:
            for sy in SGN:
                put("Joint4_%s_%s%s" % (tag, K[sx], K[sy]),
                    place_corner(j, sx, sy, z), PRINTP, g)
                n += 1
    # mid plane: only the two front posts carry a rail now
    for sx in SGN:
        put("Joint4_mid_%sm" % K[sx], place_corner(j, sx, -1, P.Z_MID), PRINTP, g)
        put("Joint4_wipe_%sm" % K[sx],
            place_corner(j, sx, -1, P.Z_WIPE), PRINTP, g)
        n += 2
    f = foot_shape()
    for sx in SGN:
        for sy in SGN:
            put("Foot_%s%s" % (K[sx], K[sy]),
                place_corner(f, sx, sy, P.Z_FOOT), PRINTP, g)
    t1 = tee_zcross_shape()
    put("TeeZCross_pp", try_(t1, P.BED_Y), PRINTP, g)
    put("TeeZCross_pm", try_(mir_y(t1), P.BED_Y), PRINTP, g)
    put("TeeZCross_mp", try_(rotz(t1, 180), P.BED_Y), PRINTP, g)
    put("TeeZCross_mm", try_(mir_y(rotz(t1, 180)), P.BED_Y), PRINTP, g)
    put("WipeBracket", wipe_bracket_shape(), PRINTP, g)
    put("Brush_brass", bx(P.WIPE_X - P.BRUSH_L / 2.0, P.WIPE_X + P.BRUSH_L / 2.0,
                          P.WIPE_Y - P.BRUSH_W / 2.0, P.WIPE_Y + P.BRUSH_W / 2.0,
                          P.BRUSH_FLOOR, P.BRUSH_FLOOR + 15.0), BRASS, g)
    return n


def wipe_bracket_shape():
    """Nozzle wipe station: clamps the front wipe rail and reaches back over
    the front frame to put a brass brush strip just under the nozzle.

    The whole bracket has to live BELOW the nozzle, because this machine moves
    the BED in Z - the gantry never lifts, so anything taller than NOZZLE_Z is
    something the toolhead will hit. That is what sets WIPE_TOP.

    No chute: the column under the purge point is clear of the bed, the bottom
    cross rails and the bed mounts all the way to the table, so purged
    filament simply falls into a bin.
    """
    X, Y = P.WIPE_X, P.WIPE_Y
    p = Pt("WipeBracket")
    b, c, h = clamp("x", (X, -P.POST_Y, P.Z_WIPE), 46.0)
    p.add(b).sub(*c)
    # web up off the sleeve, then a flange reaching back to the brush head
    p.add(bx(X - 9, X + 9, -P.POST_Y - 6, -P.POST_Y + 12, P.Z_WIPE, 485.0))
    p.add(bx(X - 9, X + 9, -P.POST_Y + 2, Y + 10, 481.0, 493.0))
    p.add(bx(X - 24, X + 24, Y - 14, Y + 11, 489.0, P.WIPE_TOP))
    # brush pocket, open at the top, plus two M3 screws into the floor
    p.sub(bx(X - P.BRUSH_L / 2.0, X + P.BRUSH_L / 2.0,
             Y - P.BRUSH_W / 2.0, Y + P.BRUSH_W / 2.0,
             P.BRUSH_FLOOR, P.WIPE_TOP + 1))
    for sx in (-1, 1):
        p.sub(cz(X + sx * 15.0, Y, 485.0, P.BRUSH_FLOOR + 1, P.M3))
    return p.build(1, "nozzle brush + purge station")


def brace_gusset_shape(name, node, brace_dir, anchor_pt, anchor_dir, normal,
                       anchor_lug):
    """Rigid two-bore gusset at one end of a diagonal: one clamp on the
    anchored tube (a post, or a rail where the posts are full), one on the
    brace, fused through a core.

    A pin-ended strut would need a bespoke fitting per angle and carry no
    moment; a two-bore clamp is one simple solid and is stiffer. The brace
    clamp lug points out of the brace plane so the bolt is reachable; the
    anchor clamp lug points away from the brace.
    """
    d = V(*brace_dir); d.normalize()
    nd = V(*normal); nd.normalize()
    node = V(*node)
    ad = V(*anchor_dir); ad.normalize()
    ap = V(*anchor_pt)
    # closest point on the anchored tube axis to the node
    t = node.sub(ap).dot(ad)
    cp = ap.add(V(ad.x * t, ad.y * t, ad.z * t))
    al = V(*anchor_lug); al.normalize()

    p = Pt(name)
    b, c, h = clamp_at((cp.x, cp.y, cp.z), (ad.x, ad.y, ad.z),
                       (al.x, al.y, al.z), P.CL_GUS)
    p.add(b).sub(*c)
    bc = node.add(V(d.x * P.BRACE_CL, d.y * P.BRACE_CL, d.z * P.BRACE_CL))
    b2, c2, _ = clamp_at((bc.x, bc.y, bc.z), (d.x, d.y, d.z),
                         (nd.x, nd.y, nd.z), P.CL_GUS)
    p.add(b2).sub(*c2)
    # Core bridging the two clamps. Both bores then have to be re-cut as LONG
    # cylinders: the clamp's own bore cut only spans the clamp length, so where
    # the core reaches past it the anchored tube would be embedded in solid.
    p.add(bx(min(cp.x, bc.x) - 12, max(cp.x, bc.x) + 12,
             min(cp.y, bc.y) - 12, max(cp.y, bc.y) + 12,
             min(cp.z, bc.z) - 12, max(cp.z, bc.z) + 12))
    LONG = 260.0
    for ctr, axis in ((cp, ad), (bc, d)):
        a0 = ctr.sub(V(axis.x * LONG, axis.y * LONG, axis.z * LONG))
        p.sub(Part.makeCylinder(P.EMT_BORE / 2.0, 2 * LONG,
                                V(a0.x, a0.y, a0.z), axis))
    p.sub(*c)
    p.sub(*c2)
    return p.build(qty=2, note="diagonal brace gusset")


def gusset_for(brace_name, end):
    """Build one gusset shape by brace name and end index (0 = p0, 1 = p1)."""
    for b in P.braces():
        if b["name"] != brace_name:
            continue
        p0, p1 = b["p0"], b["p1"]
        dv = V(*p1).sub(V(*p0))
        node = p0 if end == 0 else p1
        dirv = (dv.x, dv.y, dv.z) if end == 0 else (-dv.x, -dv.y, -dv.z)
        apt, adir = b["a0"] if end == 0 else b["a1"]
        nrm = b["n"]
        lug = ((1.0 if p0[0] > 0 else -1.0, 0.0, 0.0)) if nrm[0] else nrm
        key = brace_name.replace("Brace_", "")
        return brace_gusset_shape("Gusset_%s_%d" % (key, end), node, dirv,
                                  apt, adir, nrm, lug)
    raise KeyError(brace_name)


def stage_braces():
    """One gusset at each end of each diagonal."""
    g = "A3_Printed_Bracing"
    n = 0
    for b in P.braces():
        p0, p1 = b["p0"], b["p1"]
        d = V(*p1).sub(V(*p0))
        ends = ((0, p0, (d.x, d.y, d.z), b["a0"]),
                (1, p1, (-d.x, -d.y, -d.z), b["a1"]))
        # anchor lug points outward along the brace-plane normal
        nrm = b["n"]
        if nrm[0]:
            lug = (1.0 if b["p0"][0] > 0 else -1.0, 0.0, 0.0)
        else:
            lug = nrm
        for end, node, dirv, (apt, adir) in ends:
            key = b["name"].replace("Brace_", "")
            shp = brace_gusset_shape("Gusset_%s_%d" % (key, end),
                                     node, dirv, apt, adir, nrm, lug)
            put("Gusset_%s_%d" % (key, end), shp, PRINTP, g)
            n += 1
    return n


# ====================================================== stage 3: Z (bed) axis
def stage_z_hardware():
    """Everything here is built bed-centred and shifted forward by BED_Y."""
    g = "B1_Z_Hardware"
    dy = P.BED_Y
    for sx in SGN:
        for sy in SGN:
            put("ZRod_%s%s" % (K[sx], K[sy]),
                try_(cz(sx * P.ZROD_X, sy * P.ZROD_Y, P.ZROD_Z0,
                        P.ZROD_Z0 + P.ZROD_LEN, P.ZROD_D), dy), ROD, g)
    for sx in SGN:
        put("ZScrew_%s" % K[sx],
            try_(cz(sx * P.ZSCREW_X, 0, P.ZSCREW_Z0,
                    P.ZSCREW_Z0 + P.ZSCREW_LEN, P.ZSCREW_D), dy), BRASS, g)
        put("ZMotor_%s" % K[sx],
            try_(nema17((sx * P.ZSCREW_X, 0.0), P.ZMOT_FACE, +1), dy), MOTOR, g)
        put("ZCoupler_%s" % K[sx],
            try_(cz(sx * P.ZSCREW_X, 0, P.ZMOT_FACE + 13.0,
                    P.ZSCREW_Z0 + 11.0, 18.0), dy), MOTOR, g)
    # bed assembly, drawn at the top of travel
    put("BedPlate", try_(bx(-P.BED_PLATE / 2.0, P.BED_PLATE / 2.0,
                            -P.BED_PLATE / 2.0, P.BED_PLATE / 2.0,
                            P.BED_PLATE_BOT, P.BED_PLATE_TOP), dy),
        (0.75, 0.75, 0.78), g)
    put("BedSurface", try_(bx(-P.BED_PLATE / 2.0, P.BED_PLATE / 2.0,
                         -P.BED_PLATE / 2.0, P.BED_PLATE / 2.0,
                         P.BED_PLATE_TOP, P.BED_SURF_HIGH), dy), BEDC, g)
    return True


def zmotor_mount_shape():
    """One per side: clamps BOTH bottom cross rails, hangs the Z motor below at
    (ZSCREW_X, 0) and sockets the two Z rod bottoms above."""
    x = P.ZSCREW_X
    p = Pt("ZMotorMount")
    for sy in SGN:
        b, c, h = clamp("x", (x, sy * P.ZCROSS_Y, 0.0), P.CL_ZMOUNT, slot_deg=180.0)
        p.add(b).sub(*c)
    # spine tying the two rail clamps together
    p.add(bx(x - 16, x + 16, -P.ZCROSS_Y - 10, P.ZCROSS_Y + 10, -14.0, 14.0))
    # clearance for the motor shaft, the coupler and the screw end, which all
    # pass up the middle of the spine
    p.sub(cz(x, 0, -16.0, 16.0, 20.0))
    # lightening pockets in the spine either side of the shaft bore
    for py in (-38.0, 38.0):
        p.sub(cz(x, py, -15.0, 15.0, 18.0))
    # motor flange plate at the mounting face
    p.add(bx(x - 19, x + 19, -26, 26, P.ZMOT_FACE, P.ZMOT_FACE + 8.0))
    p.sub(cz(x, 0, P.ZMOT_FACE - 1, P.ZMOT_FACE + 9, P.N17_BOSS + 1.0))
    for sa in SGN:
        for sb in SGN:
            p.sub(cz(x + sa * P.N17_BOLT / 2.0, sb * P.N17_BOLT / 2.0,
                     P.ZMOT_FACE - 1, P.ZMOT_FACE + 9, P.M3))
    # Z rod sockets - kept clear of the conduit bores above
    for sy in SGN:
        p.add(cz(x, sy * P.ZROD_Y, 18.0, 48.0, P.ZROD_D + 2 * P.CLAMP_WALL))
        p.sub(cz(x, sy * P.ZROD_Y, 20.0, 49.0, P.ZROD_D + 0.15))
        p.sub(bx(x - 1.1, x + 1.1, sy * P.ZROD_Y, sy * (P.ZROD_Y + 14), 20.0, 49.0))
        p.sub(cx(sy * P.ZROD_Y, 40.0, x - 14, x + 14, P.M4))
    return p.build(qty=2, note="Z motor + 2 rod feet, one per side")


def bed_carriage_shape():
    """One per side: 2x LM10UU on the Z rods, T8 nut in the middle, pad under
    the bed plate. Built at the top of travel."""
    x, nz = P.ZROD_X, P.NUT_HIGH
    pad_top = P.BED_PLATE_BOT
    p = Pt("BedCarriage")
    p.add(bx(x - 16, x + 16, -P.ZROD_Y - 16, P.ZROD_Y + 16, nz - 20, nz + 20))
    for sy in SGN:
        p.add(cz(x, sy * P.ZROD_Y, nz - 20, nz + 20,
                 P.LM10_OD + 2 * P.CLAMP_WALL))
        # bore runs clear through the PAD too, not just the housing - the rod
        # continues upward past it
        p.sub(cz(x, sy * P.ZROD_Y, nz - 21, P.BED_PLATE_BOT + 1.0,
                 P.LM10_OD + 0.1))
    # anti-backlash nut: flange pocket + clearance bore
    p.add(cz(x, 0, nz - 14, nz + 14, 34.0))
    p.sub(cz(x, 0, nz - 15, nz + 15, 11.0))
    p.sub(cz(x, 0, nz - 15, nz - 4.0, 23.0))
    for i in range(4):
        a = math.radians(45 + 90 * i)
        p.sub(cz(x + 8.0 * math.cos(a), 8.0 * math.sin(a),
                 nz - 15, nz + 15, P.M3))
    # Pad reaching inboard under the bed plate. Its underside is tied to the
    # spine top rather than set by a fixed thickness: the plate is 3 mm, not
    # 6, so a fixed-thickness pad would float 7 mm clear of the spine.
    pad_z0 = nz + 20.0 - 0.5
    p.add(bx(150.0, x + 16, -70.0, 70.0, pad_z0, pad_top))
    # these take the BedMount brackets, not the bed itself
    for sy in SGN:
        for bx_, by_ in P.BM_BOLT:
            p.sub(cz(bx_, sy * by_, pad_z0 - 1.0, pad_top + 1.0, P.M4))
    # lightening pockets in the pad and in the spine between the bearings
    for py in (-48.0, -24.0, 0.0, 24.0, 48.0):
        p.sub(cz(166.0, py, pad_z0 - 1.0, pad_top + 1.0, 20.0))
    for py in (-30.0, 30.0):
        p.sub(cx(py, nz, x - 17.0, x + 17.0, 26.0))
    for py in (-63.0, 63.0):
        p.sub(cx(py, nz, x - 17.0, x + 17.0, 22.0))
    return p.build(qty=2, note="bed carriage, one per side (mirror the pair)")


def bed_mount_shape():
    """Reaches from the bed carriage pad out to ONE of the bed's own mounting
    holes at (+-BED_HOLE, +-BED_HOLE).

    The bed is a stock CR-10 plate whose holes sit on a 240 mm square, while
    the carriages are at X=+-ZROD_X with pads only +-70 in Y - the patterns do
    not meet. Drilling the plate instead is NOT an option: the heater element
    is bonded to its underside and a new hole can cut a trace.

    Section is an L. The flange tucks UNDER the carriage pad and bolts up into
    it; the riser steps up OUTBOARD of the pad (Y > 70, where there is no pad)
    to reach the plate plane. Nothing shares space with the pad, and the bed
    still lands on one flat plane.
    """
    pad_top = P.BED_PLATE_BOT
    pad_z0 = P.NUT_HIGH + 20.0 - 0.5
    p = Pt("BedMount")
    p.add(bx(112.0, P.BM_FLANGE_X1, 42.0, 73.0, pad_z0 - 9.0, pad_z0))
    p.add(bx(112.0, 142.0, 71.0, 130.0, pad_z0 - 9.0, pad_top))
    # lighten the riser, keeping material around the bed bolt
    p.sub(bx(117.0, 137.0, 76.0, 104.0, pad_z0 - 3.0, pad_top - 3.0))
    for bx_, by_ in P.BM_BOLT:
        p.sub(cz(bx_, by_, pad_z0 - 10.0, pad_z0 + 1.0, P.M4))
    # the bed bolt, nut pocket underneath
    p.sub(cz(P.BED_HOLE, P.BED_HOLE, pad_z0 - 10.0, pad_top + 1.0, P.M4))
    p.sub(cz(P.BED_HOLE, P.BED_HOLE, pad_z0 - 10.0, pad_z0 - 4.0, P.M4_HEAD))
    return p.build(qty=4, note="bed to carriage, reaches the 240 mm hole pattern")


def zrod_top_shape():
    """One per side: clamps the Z-top side rail, carries both Z rod tops."""
    x, z = P.POST_X, P.Z_ZTOP
    rt = P.ZROD_Z0 + P.ZROD_LEN
    p = Pt("ZRodTop")
    b, c, h = clamp("y", (x, 0.0, z), 110.0, slot_deg=-90.0)
    p.add(b).sub(*c)
    p.add(bx(P.ZROD_X - 14, 236.0, -P.ZROD_Y - 14, P.ZROD_Y + 14, z, z + 20))
    for sy in SGN:
        p.add(cz(P.ZROD_X, sy * P.ZROD_Y, z, rt + 5.0,
                 P.ZROD_D + 2 * P.CLAMP_WALL))
        p.sub(cz(P.ZROD_X, sy * P.ZROD_Y, z - 1.0, rt + 6.0, P.ZROD_D + 0.15))
    # the T8 screw runs up through this arm at Y=0 - it needs to pass
    p.sub(cz(P.ZSCREW_X, 0.0, z - 1.0, z + 21.0, P.ZSCREW_D + 6.0))
    # lightening pockets: the arm between the rod bosses and the screw is a
    # plain slab carrying almost nothing
    for px in (177.0, 199.0, 221.0):
        for py in (-30.0, 30.0):
            p.sub(cz(px, py, z - 2.0, z + 22.0, 20.0))
    for py in (-62.0, 62.0):
        p.sub(cz(200.0, py, z - 2.0, z + 22.0, 20.0))
    return p.build(qty=2, note="Z rod top brackets")


def stage_z_printed():
    g = "B2_Printed_Z"
    dy = P.BED_Y
    m = zmotor_mount_shape()
    put("ZMotorMount_p", try_(m, dy), PRINTP, g)
    put("ZMotorMount_m", try_(mir_x(m), dy), PRINTP, g)
    c = bed_carriage_shape()
    put("BedCarriage_p", try_(c, dy), PRINTP, g)
    put("BedCarriage_m", try_(mir_x(c), dy), PRINTP, g)
    bm = bed_mount_shape()
    put("BedMount_pp", try_(bm, dy), PRINTP, g)
    put("BedMount_pm", try_(mir_y(bm), dy), PRINTP, g)
    put("BedMount_mp", try_(mir_x(bm), dy), PRINTP, g)
    put("BedMount_mm", try_(mir_x(mir_y(bm)), dy), PRINTP, g)
    return True
