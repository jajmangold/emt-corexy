# -*- coding: utf-8 -*-
"""Is each printed part actually printable? Run inside FreeCAD.

Two questions, answered from the geometry rather than asserted:

  1. BED CONTACT - in some orientation, does the part have a genuine PLANAR
     face at its lowest extreme, with enough area to hold it down?
  2. OVERHANGS - in that orientation, how much downward-facing area is steeper
     than 45 degrees and not already on the bed?

Getting a face's OUTWARD normal right is the whole ballgame here, and the
Orientation == "Reversed" flag is not a reliable way to do it: the pad face of
FootPad reports "Reversed" while normalAt() already returns the correct
outward (0,0,-1), so flipping on that flag pointed it upward and hid a
2463 mm2 bed face. Probe the solid instead - step a little along the candidate
normal and ask whether that point is inside. That is unambiguous.
"""
import math
import FreeCAD as App
from FreeCAD import Vector as V

import params as P

UPS = (("+Z", V(0, 0, 1)), ("-Z", V(0, 0, -1)),
       ("+X", V(1, 0, 0)), ("-X", V(-1, 0, 0)),
       ("+Y", V(0, 1, 0)), ("-Y", V(0, -1, 0)))

SUPPORT_COS = math.sin(math.radians(45.0))   # 0.707


def face_normal(f, solid=None):
    try:
        u, v = f.Surface.parameter(f.CenterOfMass)
        n = f.normalAt(u, v)
    except Exception:
        return None
    if solid is not None:
        c = f.CenterOfMass
        probe = V(c.x + n.x * 0.1, c.y + n.y * 0.1, c.z + n.z * 0.1)
        try:
            if solid.isInside(probe, 1e-7, True):
                n = V(-n.x, -n.y, -n.z)      # it pointed inward
        except Exception:
            pass
    return n


def along(p, up):
    return p.x * up.x + p.y * up.y + p.z * up.z


def assess(shape, tol=0.05):
    """For each of 6 orientations: planar bed-contact area, overhang area,
    and the footprint / height in that orientation."""
    out = {}
    faces = [(f, face_normal(f, shape)) for f in shape.Faces]
    # Extents come from the BOUNDING BOX, not the vertexes: a full circle has
    # a single seam vertex, so a vertex-based extent simply loses round
    # features - it reported FootPad's 56 mm pad as a 26 mm footprint.
    bb = shape.optimalBoundingBox()
    ext = {"+Z": (bb.ZMin, bb.ZMax), "-Z": (-bb.ZMax, -bb.ZMin),
           "+X": (bb.XMin, bb.XMax), "-X": (-bb.XMax, -bb.XMin),
           "+Y": (bb.YMin, bb.YMax), "-Y": (-bb.YMax, -bb.YMin)}
    dims = {"X": bb.XLength, "Y": bb.YLength, "Z": bb.ZLength}
    for name, up in UPS:
        lo, hi = ext[name]
        contact = 0.0
        overhang = 0.0
        bridge = 0.0
        steep = 0.0
        span = 0.0
        for f, n in faces:
            if n is None:
                continue
            d = n.x * up.x + n.y * up.y + n.z * up.z
            if d > -SUPPORT_COS:
                continue                      # vertical-ish or upward: fine
            at_bed = abs(along(f.CenterOfMass, up) - lo) < tol
            planar = f.Surface.__class__.__name__ == "Plane"
            if at_bed and planar and d < -0.999:
                contact += f.Area
            elif not at_bed:
                overhang += f.Area
                # A near-horizontal underside is a BRIDGE - routine on FDM if
                # the span is short. Between 45 and ~72 degrees is the case
                # that actually wants support.
                if d < -0.95:
                    bridge += f.Area
                    fb = f.BoundBox
                    sp = sorted([fb.XLength, fb.YLength, fb.ZLength])
                    # the slicer bridges across the SHORTER in-plane dimension
                    span = max(span, sp[1])
                else:
                    steep += f.Area
        perp = [dims[k] for k in "XYZ" if k != name[1]]
        out[name] = dict(contact=contact, overhang=overhang, bridge=bridge,
                         span=span,
                         steep=steep, height=hi - lo,
                         footprint=sorted(perp, reverse=True))
    return out


def best(shape, min_contact=150.0):
    """Pick an orientation balancing bed contact against STEEP overhang (the
    kind that needs support); bridges are not penalised. Returns
    (name, info, fits_envelope)."""
    a = assess(shape)

    def score(kv):
        # Lower is better. Steep overhang is the worst (needs support), then
        # long bridges (sag), and bed contact is only worth chasing up to the
        # point where it holds: maximising contact alone picked a 61 mm bridge
        # over a 23 mm one to gain 65 mm2 of bed area.
        i = kv[1]
        return (i["steep"] * 2.0
                + max(0.0, i["span"] - 25.0) * 60.0
                - 4.0 * min(i["contact"], 1200.0))

    ranked = sorted(a.items(), key=score)
    for name, info in ranked:
        fp = info["footprint"]
        fits = (fp[0] <= P.PRINT_ENV[0] and fp[1] <= P.PRINT_ENV[1]
                and info["height"] <= P.PRINT_ENV[2])
        if fits and info["contact"] >= min_contact:
            return name, info, True
    name, info = ranked[0]
    fp = info["footprint"]
    fits = (fp[0] <= P.PRINT_ENV[0] and fp[1] <= P.PRINT_ENV[1]
            and info["height"] <= P.PRINT_ENV[2])
    return name, info, fits
