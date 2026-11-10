# -*- coding: utf-8 -*-
"""Pose-sampled axis-aligned collision check for the EMT CoreXY.

Per-axis "clearance" numbers are not a collision test: two bodies that overlap
in Z are fine if they are separated in X. So every component here is declared
as a LIST OF BOXES at its true shape, the moving assemblies are rebuilt at
sampled poses, and every pair is tested for real 3D overlap.

Pure Python / no OCCT: this runs in milliseconds and cannot crash FreeCAD.
It is the authority on fit; the solid model must agree with it.
"""
import itertools
import params as P

# Pairs closer than this are reported. EMT_GAP is the tightest INTENTIONAL
# clearance in the frame - a rail is meant to stop that far off the post, and
# at a corner the two perpendicular rails come that close to each other too -
# so the threshold sits just under it. A real overlap still reads <= 0.
MIN_CLEAR = 0.4


def B(x0, x1, y0, y1, z0, z1):
    return (min(x0, x1), max(x0, x1), min(y0, y1), max(y0, y1),
            min(z0, z1), max(z0, z1))


def gap(a, b):
    """Signed separation: >0 apart by that much, <=0 interpenetrating."""
    return max(max(a[0] - b[1], b[0] - a[1]),
               max(a[2] - b[3], b[2] - a[3]),
               max(a[4] - b[5], b[4] - a[5]))


def pair_gap(A, Bs):
    return min(gap(a, b) for a in A for b in Bs)


E = P.EMT_OD / 2.0
RH = P.RAIL_X_LEN / 2.0
RHY = P.RAIL_Y_LEN / 2.0
BY = P.BED_Y          # the bed / Z subsystem is shifted forward by this
TY = P.BELT_TURN_Y


# --------------------------------------------------------------- static frame
def statics():
    S = {}
    for sx in (-1, 1):
        for sy in (-1, 1):
            n = "post_%s%s" % ("p" if sx > 0 else "m", "p" if sy > 0 else "m")
            S[n] = [B(sx * P.POST_X - E, sx * P.POST_X + E,
                      sy * P.POST_Y - E, sy * P.POST_Y + E, P.Z_FOOT, P.Z_CAP)]
    for z, tag in ((P.Z_BOT, "bot"), (P.Z_CAP, "cap")):
        for sy in (-1, 1):
            S["railX_%s_%s" % (tag, "p" if sy > 0 else "m")] = [
                B(-RH, RH, sy * P.POST_Y - E, sy * P.POST_Y + E, z - E, z + E)]
        for sx in (-1, 1):
            S["railY_%s_%s" % (tag, "p" if sx > 0 else "m")] = [
                B(sx * P.POST_X - E, sx * P.POST_X + E, -RHY, RHY, z - E, z + E)]
    S["railX_mid_m"] = [B(-RH, RH, -P.POST_Y - E, -P.POST_Y + E,
                          P.Z_MID - E, P.Z_MID + E)]
    S["railX_wipe_m"] = [B(-RH, RH, -P.POST_Y - E, -P.POST_Y + E,
                           P.Z_WIPE - E, P.Z_WIPE + E)]
    # wipe station: three boxes, because one box over the whole bracket would
    # reach the brush head's Y and the sleeve's Z at once and read as a slab
    # sitting in the bed's path
    S["wipe_bracket"] = [
        B(P.WIPE_X - 23, P.WIPE_X + 23,
          -P.POST_Y - 14, -P.POST_Y + 14, P.Z_WIPE - 25, P.Z_WIPE + 14),
        B(P.WIPE_X - 9, P.WIPE_X + 9,
          -P.POST_Y - 6, P.WIPE_Y + 10, P.Z_WIPE, 493.0),
        B(P.WIPE_X - 24, P.WIPE_X + 24,
          P.WIPE_Y - 14, P.WIPE_Y + 11, 489.0, P.WIPE_TOP)]
    # the brush itself, bristles included - the ONE thing the nozzle may touch
    S["brush"] = [B(P.WIPE_X - P.BRUSH_L / 2.0, P.WIPE_X + P.BRUSH_L / 2.0,
                    P.WIPE_Y - P.BRUSH_W / 2.0, P.WIPE_Y + P.BRUSH_W / 2.0,
                    P.BRUSH_FLOOR, P.BRUSH_FLOOR + 15.0)]
    for sy in (-1, 1):
        S["railX_zcross_%s" % ("p" if sy > 0 else "m")] = [
            B(-RH, RH, BY + sy * P.ZCROSS_Y - E, BY + sy * P.ZCROSS_Y + E,
              P.Z_BOT - E, P.Z_BOT + E)]
    # diagonals, chopped into segments - a diagonal's own AABB spans most of
    # the machine and would be useless as a proxy
    NSEG = 16
    for _b in P.braces():
        nm, p0, p1 = _b["name"], _b["p0"], _b["p1"]
        segs = []
        for i in range(NSEG):
            t0, t1 = i / float(NSEG), (i + 1) / float(NSEG)
            a = [p0[k] + (p1[k] - p0[k]) * t0 for k in range(3)]
            b = [p0[k] + (p1[k] - p0[k]) * t1 for k in range(3)]
            segs.append(B(min(a[0], b[0]) - E, max(a[0], b[0]) + E,
                          min(a[1], b[1]) - E, max(a[1], b[1]) + E,
                          min(a[2], b[2]) - E, max(a[2], b[2]) + E))
        S[nm.lower()] = segs

    # ---- Z axis statics, all shifted forward with the bed
    r = P.ZROD_D / 2.0
    for sx in (-1, 1):
        for sy in (-1, 1):
            S["zrod_%s%s" % ("p" if sx > 0 else "m", "p" if sy > 0 else "m")] = [
                B(sx * P.ZROD_X - r, sx * P.ZROD_X + r,
                  BY + sy * P.ZROD_Y - r, BY + sy * P.ZROD_Y + r,
                  P.ZROD_Z0, P.ZROD_Z0 + P.ZROD_LEN)]
    s = P.ZSCREW_D / 2.0
    for sx in (-1, 1):
        k = "p" if sx > 0 else "m"
        S["zscrew_%s" % k] = [B(sx * P.ZSCREW_X - s, sx * P.ZSCREW_X + s,
                                BY - s, BY + s,
                                P.ZSCREW_Z0, P.ZSCREW_Z0 + P.ZSCREW_LEN)]
        S["zmotor_%s" % k] = [B(sx * P.ZSCREW_X - P.N17H,
                                sx * P.ZSCREW_X + P.N17H,
                                BY - P.N17H, BY + P.N17H,
                                P.ZMOT_FACE - P.N17_LEN, P.ZMOT_FACE)]
        S["zcoupler_%s" % k] = [B(sx * P.ZSCREW_X - 9, sx * P.ZSCREW_X + 9,
                                  BY - 9, BY + 9,
                                  P.ZMOT_FACE + 13, P.ZSCREW_Z0 + 11)]

    # ---- gantry statics
    yr = P.YROD_D / 2.0
    for sx in (-1, 1):
        S["yrod_%s" % ("p" if sx > 0 else "m")] = [
            B(sx * P.YROD_X - yr, sx * P.YROD_X + yr,
              -P.YROD_LEN / 2.0, P.YROD_LEN / 2.0,
              P.YROD_Z - yr, P.YROD_Z + yr)]

    def pulbox(c, z0, z1):
        f = P.PULLEY_FL / 2.0
        return B(c[0] - f, c[0] + f, c[1] - f, c[1] + f, z0, z1)

    S["A_motor"] = [B(P.A_MOTOR[0] - P.N17H, P.A_MOTOR[0] + P.N17H,
                      P.A_MOTOR[1] - P.N17H, P.A_MOTOR[1] + P.N17H,
                      P.A_BODY_BOT, P.A_BODY_TOP),
                    pulbox(P.A_MOTOR, P.BELT_Z_A - P.PULLEY_H / 2.0,
                           P.BELT_Z_A + P.PULLEY_H / 2.0)]
    S["B_motor"] = [B(P.B_MOTOR[0] - P.N17H, P.B_MOTOR[0] + P.N17H,
                      P.B_MOTOR[1] - P.N17H, P.B_MOTOR[1] + P.N17H,
                      P.B_BODY_BOT, P.B_BODY_TOP),
                    pulbox(P.B_MOTOR, P.BELT_Z_B - P.PULLEY_H / 2.0,
                           P.BELT_Z_B + P.PULLEY_H / 2.0)]
    S["A_idler"] = [pulbox(P.A_IDLER, P.BELT_Z_A - P.PULLEY_H / 2.0,
                           P.BELT_Z_A + P.PULLEY_H / 2.0)]
    S["B_idler"] = [pulbox(P.B_IDLER, P.BELT_Z_B - P.PULLEY_H / 2.0,
                           P.BELT_Z_B + P.PULLEY_H / 2.0)]
    return S


# ------------------------------------------------------------ moving assemblies
YC_WEB_X0 = 200.0
YC_WEB_X1 = P.YC_WEB_X1
YC_HOUS_X0 = P.YROD_X - P.LM12_OD / 2.0 - P.CLAMP_WALL
YC_HOUS_X1 = P.YC_X1
YC_HOUS_Z0 = P.YROD_Z - P.LM12_OD / 2.0 - P.CLAMP_WALL
YC_HOUS_Z1 = P.YC_Z1
XC_Z0 = P.BELT_Z_B - P.PULLEY_H / 2.0 - 7.0
XC_Z1 = P.BELT_Z_A + P.PULLEY_H / 2.0 + 7.0
BH = P.XBEAM_SQ / 2.0


def x_beam(gy):
    """2020 extrusion plus the MGN12 rail on its front face."""
    return [B(-P.XBEAM_LEN / 2.0, P.XBEAM_LEN / 2.0,
              gy - BH, gy + BH, P.XBEAM_Z - BH, P.XBEAM_Z + BH),
            B(-P.XBEAM_LEN / 2.0, P.XBEAM_LEN / 2.0,
              gy + P.MGN12_RAIL_Y0, gy + P.MGN12_RAIL_Y1,
              P.XBEAM_Z - P.MGN12_RAIL_ZH, P.XBEAM_Z + P.MGN12_RAIL_ZH)]


def y_carriage(gy, sx):
    """Four boxes matching the real part, because the clearances here are small
    enough that one coarse box gives false hits: the idler fork reaches inboard
    to x=190, right over the Z screw, and it is Z that separates them (fork
    bottom 515 vs screw top 513)."""
    h = P.YC_LEN / 2.0
    BHl = P.XBEAM_SQ / 2.0
    fork = B(sx * 190.0, sx * 219.0, gy + TY - 14, gy + TY + 14,
             P.BELT_Z_B - 11.0, P.BELT_Z_A + 11.0)
    clamp = B(sx * 203.0, sx * 239.0, gy - BHl - 7, gy + BHl + 7,
              P.XBEAM_Z - BHl - 8, P.XBEAM_Z + BHl + 8)
    web = B(sx * 227.0, sx * 250.0, gy - h, gy + h,
            P.XBEAM_Z + 8, P.YROD_Z - 2)
    hous = B(sx * YC_HOUS_X0, sx * YC_HOUS_X1, gy - h, gy + h,
             YC_HOUS_Z0, YC_HOUS_Z1)
    return [fork, clamp, web, hous]


def x_carriage(gx, gy):
    """MGN12 block in front of the rail, belt clamps behind the extrusion,
    joined over and under it - so it wraps the beam."""
    return [B(gx - P.MGN12_BLOCK_L / 2.0, gx + P.MGN12_BLOCK_L / 2.0,
              gy + P.MGN12_RAIL_Y0 - P.MGN12_BLOCK_H, gy + P.MGN12_RAIL_Y1,
              P.XBEAM_Z - P.MGN12_BLOCK_W / 2.0,
              P.XBEAM_Z + P.MGN12_BLOCK_W / 2.0),
            B(gx - P.XC_HALF, gx + P.XC_HALF,
              gy + BH, gy + P.BELT_BEAM_Y + 8.0, XC_Z0, XC_Z1)]


def toolhead(gx, gy):
    """Stock Voron Stealthburner + CW2.5, MEASURED envelope. It hangs forward:
    nozzle at gy + BED_Y, body from nozzle-39.60 to nozzle+34.10."""
    ny = gy + P.BED_Y
    return [B(gx - 40.90, gx + 35.53, ny - 39.60, ny + 34.10,
              P.NOZZLE_Z, P.NOZZLE_Z + 158.23)]


def bed(nz):
    return [B(-P.BED_PLATE / 2.0, P.BED_PLATE / 2.0,
              BY - P.BED_PLATE / 2.0, BY + P.BED_PLATE / 2.0,
              nz + P.BED_RISE - P.BED_STACK - P.BED_PLATE_T, nz + P.BED_RISE)]


def bed_carriage(nz, sx):
    top = nz + P.BED_RISE - P.BED_STACK - P.BED_PLATE_T
    return [B(sx * P.ZROD_X - 28, sx * P.ZROD_X + 28, BY - 75, BY + 75,
              nz - 20, top),
            B(sx * 150.0, sx * (P.ZROD_X + 28), BY - 70, BY + 70, nz + 20, top),
            # BedMount brackets out to the bed's own 240 mm hole pattern
            B(sx * 112.0, sx * 196.0, BY - 130, BY + 130, top - 9.0, top)]


# pairs that are SUPPOSED to touch
ALLOWED = [
    ("post", "railX"), ("post", "railY"), ("railX_zcross", "railY_bot"),
    ("brace", "post"), ("brace", "railX_bot"), ("brace", "railY_bot"),
    ("brace", "railX_gan"), ("brace", "railY_gan"), ("brace", "railX_cap"),
    ("brace", "railY_cap"),
    ("zrod", "bed_carriage"), ("zscrew", "bed_carriage"),
    ("zrod", "railX_zcross"),
    ("zscrew", "zcoupler"), ("zcoupler", "zmotor"),
    ("zmotor", "railX_zcross"),
    ("yrod", "y_carriage"), ("yrod", "railY_gan"),
    ("x_beam", "y_carriage"), ("x_beam", "x_carriage"),
    ("x_carriage", "toolhead"), ("toolhead", "bed"),
    # the toolhead's rear face IS the rail front face by definition -
    # the MGN12 block sits between them
    ("toolhead", "x_beam"),
    ("bed_carriage", "bed"),
    # the wipe station: the bracket clamps its rail and holds the brush, and
    # the nozzle is MEANT to touch the bristles
    ("wipe_bracket", "railX_wipe"), ("wipe_bracket", "brush"),
    ("toolhead", "brush"),
]


def allowed(a, b):
    for u, v in ALLOWED:
        if (a.startswith(u) and b.startswith(v)) or \
           (a.startswith(v) and b.startswith(u)):
            return True
    return False


def run(nx=5, ny=5, nz=5):
    S = statics()
    hx, hy = P.BUILD_X / 2.0, P.BUILD_Y / 2.0
    gxs = [-hx + 2 * hx * i / float(nx - 1) for i in range(nx)]
    gys = [-hy + 2 * hy * i / float(ny - 1) for i in range(ny)]
    nzs = [P.NUT_LOW + (P.NUT_HIGH - P.NUT_LOW) * i / float(nz - 1)
           for i in range(nz)]
    worst = {}

    def note(a, b, g):
        if allowed(a, b):
            return
        k = (a, b) if a < b else (b, a)
        if k not in worst or g < worst[k]:
            worst[k] = g

    for a, b in itertools.combinations(sorted(S), 2):
        note(a, b, pair_gap(S[a], S[b]))

    for gx in gxs:
        for gy in gys:
            mov = {"y_carriage_m": y_carriage(gy, -1),
                   "y_carriage_p": y_carriage(gy, +1),
                   "x_beam": x_beam(gy),
                   "x_carriage": x_carriage(gx, gy),
                   "toolhead": toolhead(gx, gy)}
            for mn, mb in mov.items():
                for sn, sb in S.items():
                    note(mn, sn, pair_gap(mb, sb))
            for a, b in itertools.combinations(sorted(mov), 2):
                note(a, b, pair_gap(mov[a], mov[b]))
            for nzv in nzs:
                beds = {"bed": bed(nzv),
                        "bed_carriage_m": bed_carriage(nzv, -1),
                        "bed_carriage_p": bed_carriage(nzv, +1)}
                for mn, mb in mov.items():
                    for bn, bb in beds.items():
                        note(mn, bn, pair_gap(mb, bb))

    for nzv in nzs:
        beds = {"bed": bed(nzv),
                "bed_carriage_m": bed_carriage(nzv, -1),
                "bed_carriage_p": bed_carriage(nzv, +1)}
        for bn, bb in beds.items():
            for sn, sb in S.items():
                note(bn, sn, pair_gap(bb, sb))
        for a, b in itertools.combinations(sorted(beds), 2):
            note(a, b, pair_gap(beds[a], beds[b]))

    bad = {k: v for k, v in worst.items() if v < MIN_CLEAR}
    return worst, bad
