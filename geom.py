# -*- coding: utf-8 -*-
"""EMT CoreXY - geometry builder. Run stages from the FreeCAD RPC.

Conventions that are NOT optional here:
  * every shape is built at its ABSOLUTE coordinates and assigned to a
    Part::Feature whose Placement stays identity (freecad-placement-bakes-into-shape)
  * every printed union overlaps by >= OV; nothing is ever tangent
    (freecad-tangent-non-manifold)
  * conduit and rod are modelled SOLID - the bore is irrelevant to the design
    and 20 extra cuts is 20 chances to crash the kernel
    (freecad-mcp-heavy-booleans)
"""
import math
import FreeCAD as App
import Part
from FreeCAD import Vector as V

import params as P

DOCNAME = "EMT_CoreXY"

STEEL  = (0.55, 0.57, 0.60)
ROD    = (0.80, 0.82, 0.85)
BRASS  = (0.72, 0.60, 0.25)
PRINTP = (0.25, 0.55, 0.85)
MOTOR  = (0.18, 0.18, 0.20)
BELTC  = (0.12, 0.12, 0.12)
BEDC   = (0.70, 0.45, 0.30)

# registry of printed parts: name -> (shape, qty, note)
PRINTED = {}


# ----------------------------------------------------------------- document
def doc():
    try:
        return App.getDocument(DOCNAME)
    except Exception:
        d = App.newDocument(DOCNAME)
        return d


def group(name):
    d = doc()
    g = d.getObject(name)
    if g is None:
        g = d.addObject("App::DocumentObjectGroup", name)
    return g


def put(name, shape, color=None, grp=None, transp=0):
    d = doc()
    o = d.getObject(name)
    if o is None:
        o = d.addObject("Part::Feature", name)
    o.Shape = shape
    vo = getattr(o, "ViewObject", None)       # None under freecadcmd
    if vo is not None:
        if color:
            vo.ShapeColor = color
        vo.Transparency = transp
    if grp:
        g = group(grp)
        if o.Name not in [x.Name for x in g.Group]:
            g.addObject(o)
    return o


def clear():
    d = doc()
    for o in list(d.Objects):
        try:
            d.removeObject(o.Name)
        except Exception:
            pass
    PRINTED.clear()


# --------------------------------------------------------------- primitives
def bx(x0, x1, y0, y1, z0, z1):
    """Bounds are normalised: callers may pass them in either order, which
    matters because mirrored features arrive with their signs flipped."""
    x0, x1 = min(x0, x1), max(x0, x1)
    y0, y1 = min(y0, y1), max(y0, y1)
    z0, z1 = min(z0, z1), max(z0, z1)
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))


def cz(x, y, z0, z1, d):
    z0, z1 = min(z0, z1), max(z0, z1)
    return Part.makeCylinder(d / 2.0, z1 - z0, V(x, y, z0), V(0, 0, 1))


def cx(y, z, x0, x1, d):
    x0, x1 = min(x0, x1), max(x0, x1)
    return Part.makeCylinder(d / 2.0, x1 - x0, V(x0, y, z), V(1, 0, 0))


def cyl_y(x, z, y0, y1, d):
    y0, y1 = min(y0, y1), max(y0, y1)
    return Part.makeCylinder(d / 2.0, y1 - y0, V(x, y0, z), V(0, 1, 0))


def xform(shape, pos=(0, 0, 0), rot=None):
    s = shape.copy()
    s.Placement = App.Placement(V(*pos), rot if rot is not None else App.Rotation())
    return s


class Pt(object):
    """Accumulate adds and subs, fuse once, cut once."""

    def __init__(self, name):
        self.name = name
        self.a = []
        self.s = []

    def add(self, *sh):
        self.a.extend([x for x in sh if x is not None])
        return self

    def sub(self, *sh):
        self.s.extend([x for x in sh if x is not None])
        return self

    def build(self, qty=1, note=""):
        b = self.a[0]
        for x in self.a[1:]:
            b = b.fuse(x)
        if self.s:
            c = self.s[0]
            for x in self.s[1:]:
                c = c.fuse(x)
            b = b.cut(c)
        b = b.removeSplitter()
        PRINTED[self.name] = (b, qty, note)
        return b


# ------------------------------------------------------- pinch tube clamp
# Canonical frame: sleeve along +Z centred at origin, pinch slot opens toward +X.
def clamp_parts(L, bore=None, wall=None, boltd=None, nut_af=None):
    """Canonical pinch clamp: bore along +Z, pinch slot opening toward +X,
    bolt along Y.

    This was a solid rectangular block, which is the worst shape possible: of a
    39 x 29 x 46 block only 36% was the load-bearing annulus and 64% was corner
    material carrying nothing. It is now a thin SLEEVE plus a single bolt lug -
    the shape Maker Pipe and every shaft collar uses - and one bolt per joint
    rather than a full-length lug. Everything in the machine clamps conduit
    through this one function, so the saving propagates everywhere.
    """
    bore = P.EMT_BORE if bore is None else bore
    wall = P.CLAMP_WALL if wall is None else wall
    boltd = P.M4 if boltd is None else boltd
    nut_af = P.M4_NUT_AF if nut_af is None else nut_af
    r = bore / 2.0 + wall
    bolt_x = r + 5.5
    lug_x = bolt_x + 5.5
    lug_w = 17.0
    lug_len = min(24.0, L)

    body = cz(0, 0, -L / 2.0, L / 2.0, 2 * r)
    # bolt lug, overlapping the sleeve so the fuse is never tangent
    body = body.fuse(bx(r - 3.0, lug_x, -lug_w / 2.0, lug_w / 2.0,
                        -lug_len / 2.0, lug_len / 2.0))

    cuts = [cz(0, 0, -L / 2.0 - 1, L / 2.0 + 1, bore),
            # pinch slot: must run the FULL sleeve length or it cannot close
            bx(0, lug_x + 1, -P.SLOT_W / 2.0, P.SLOT_W / 2.0,
               -L / 2.0 - 1, L / 2.0 + 1)]
    cuts.append(cyl_y(bolt_x, 0, -lug_w, lug_w, boltd))
    cuts.append(cyl_y(bolt_x, 0, -lug_w, -lug_w / 2.0 + 3.5, P.M4_HEAD))
    cuts.append(bx(bolt_x - nut_af / 2.0, bolt_x + nut_af / 2.0,
                   lug_w / 2.0 - 4.0, lug_w, -nut_af / 2.0, nut_af / 2.0))
    return body, cuts, r


ROT = {
    "z": App.Rotation(),
    "y": App.Rotation(V(1, 0, 0), -90),
    "x": App.Rotation(V(0, 1, 0), 90),
}


def basis_placement(pos, ex, ey, ez):
    m = App.Matrix(ex.x, ey.x, ez.x, pos.x,
                   ex.y, ey.y, ez.y, pos.y,
                   ex.z, ey.z, ez.z, pos.z,
                   0.0, 0.0, 0.0, 1.0)
    return App.Placement(m)


def clamp_at(pos, ez, ex, L, bore=None, wall=None, boltd=None):
    """Pinch clamp with its bore along ez and its pinch lug along ex, for
    arbitrary directions - the diagonal braces are not axis-aligned."""
    body, cuts, h = clamp_parts(L, bore, wall, boltd)
    ez = V(*ez); ez.normalize()
    ex = V(*ex); ex.normalize()
    ey = ez.cross(ex); ey.normalize()
    ex = ey.cross(ez); ex.normalize()
    pl = basis_placement(V(*pos), ex, ey, ez)

    def xf(sh):
        t = sh.copy()
        t.Placement = pl
        return t

    return xf(body), [xf(c) for c in cuts], h


def clamp(axis, pos, L, slot_deg=0.0, bore=None, wall=None, boltd=None):
    """Return (body, cuts) for a pinch clamp whose bore axis is `axis`,
    centred at `pos`. slot_deg rolls the pinch slot about the bore axis."""
    body, cuts, h = clamp_parts(L, bore, wall, boltd)
    r = App.Rotation(V(0, 0, 1), slot_deg).multiply(App.Rotation())
    # roll first (about canonical +Z = bore axis), then orient the axis
    rot = ROT[axis].multiply(App.Rotation(V(0, 0, 1), slot_deg))
    return (xform(body, pos, rot), [xform(c, pos, rot) for c in cuts], h)


# ------------------------------------------------------------- hardware
def emt(p0, p1):
    d = V(*p1).sub(V(*p0))
    return Part.makeCylinder(P.EMT_OD / 2.0, d.Length, V(*p0), d.normalize())


def nema17(face_xy, face_z, updown=+1):
    """Motor body hanging away from its mounting face. updown=+1 -> shaft up,
    body below the face; -1 -> shaft down, body above the face."""
    x, y = face_xy
    s = updown
    z0 = face_z - s * P.N17_LEN
    body = bx(x - P.N17_SQ / 2.0, x + P.N17_SQ / 2.0,
              y - P.N17_SQ / 2.0, y + P.N17_SQ / 2.0,
              min(z0, face_z), max(z0, face_z))
    boss = cz(x, y, min(face_z, face_z + s * 2.0), max(face_z, face_z + s * 2.0),
              P.N17_BOSS)
    shaft = cz(x, y, min(face_z, face_z + s * P.N17_SHAFT_L),
               max(face_z, face_z + s * P.N17_SHAFT_L), P.N17_SHAFT_D)
    return body.fuse(boss).fuse(shaft)


def pulley(x, y, z):
    pr = P.PULLEY_PR
    core = cz(x, y, z - P.PULLEY_H / 2.0, z + P.PULLEY_H / 2.0, 2 * pr)
    f1 = cz(x, y, z - P.PULLEY_H / 2.0, z - P.PULLEY_H / 2.0 + 1.5, P.PULLEY_FL)
    f2 = cz(x, y, z + P.PULLEY_H / 2.0 - 1.5, z + P.PULLEY_H / 2.0, P.PULLEY_FL)
    return core.fuse(f1).fuse(f2)


def belt_run(p0, p1, z):
    """A flat belt run from p0=(x,y) to p1=(x,y) in plane z."""
    a, b = V(p0[0], p0[1], z), V(p1[0], p1[1], z)
    d = b.sub(a)
    L = d.Length
    if L < 1e-6:
        return None
    n = d.normalize()
    # belt cross-section: BELT_T across the run, BELT_W vertical
    box = bx(0, L, -P.BELT_T / 2.0, P.BELT_T / 2.0, -P.BELT_W / 2.0, P.BELT_W / 2.0)
    ang = math.degrees(math.atan2(n.y, n.x))
    return xform(box, (a.x, a.y, z), App.Rotation(V(0, 0, 1), ang))
