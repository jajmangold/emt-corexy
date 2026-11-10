# -*- coding: utf-8 -*-
"""Render every image and GIF used by README.md and ASSEMBLY.md.

**Needs the FreeCAD GUI** - it renders through the 3D viewer, so it cannot run
under FreeCADCmd like the rest of the project. Run it from the GUI's Python
console after the model is built:

    import build, make_media
    build.main(write=False, save=False, docs=False)   # draw the model
    make_media.main()                                  # ~3 min

Output goes to docs/img/. The files are committed, so you only need to re-run
this when the geometry actually changes.

The assembly steps are not a hand-written list of parts: each step claims a set
of name prefixes, and `check_steps()` asserts that every object in the document
is claimed by exactly one step. A mistyped prefix therefore fails loudly
instead of quietly rendering a step in which nothing new appears.
"""
import os
import sys

import FreeCAD as App
from FreeCAD import Vector as V

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import params as P                                        # noqa: E402
import render as R                                        # noqa: E402

IMG = os.path.join(HERE, "docs", "img")
TMP = os.path.join(HERE, "docs", "_frames")

W, H = 900, 740            # stills
GW, GH = 520, 440          # gif frames

AZ, EL = 38.0, 22.0        # the house three-quarter view

DONE = (0.60, 0.62, 0.66)  # already built, pushed back
NEW = (1.00, 0.52, 0.09)   # what this step adds


from steps import STEPS, starts            # noqa: E402

# Parts that move, for the motion animation.
GANTRY_Y = ("XBeam_", "MGN12_", "YCarriage", "YC_Idler", "XCarriage",
            "Stealthburner", "Nozzle")
CARRIAGE_X = ("MGN12_Block", "XCarriage", "Stealthburner", "Nozzle")
BED_Z = ("BedPlate", "BedSurface", "BedCarriage", "BedMount")
BELTS = ("BeltA", "BeltB")
# The conduit does NOT move in the exploded view. Exploding it too just makes
# the frame fall apart and you lose the reference that tells you where each
# printed part belongs.
EXPLODE_FIXED = ("Post_", "RailX", "RailY", "Brace_")


def doc():
    return App.getDocument(R.DOCNAME)


def solids(d):
    """Real geometry only. `hasattr(o, "Shape")` is NOT enough - a
    DocumentObjectGroup answers to it and then blows up on .Placement."""
    return [o for o in d.Objects if o.isDerivedFrom("Part::Feature")]


def check_steps(d):
    """Every object claimed by exactly one step. Returns a list of problems."""
    names = [o.Name for o in d.Objects
             if o.TypeId != "App::DocumentObjectGroup"]
    bad = []
    for n in names:
        hits = [t for t, pre, _ in STEPS if starts(n, pre)]
        if len(hits) == 0:
            bad.append("%s is in no assembly step" % n)
        elif len(hits) > 1:
            bad.append("%s claimed by %d steps: %s" % (n, len(hits), hits))
    for title, pre, _ in STEPS:
        if not any(starts(n, pre) for n in names):
            bad.append("step %r matches nothing" % title)
    return bad


# ------------------------------------------------------------ appearance
def save_look(d):
    look = {}
    for o in d.Objects:
        vo = getattr(o, "ViewObject", None)
        if vo is not None and hasattr(vo, "ShapeColor"):
            look[o.Name] = (vo.ShapeColor, vo.Transparency, vo.Visibility)
    return look


def restore_look(d, look):
    for o in d.Objects:
        vo = getattr(o, "ViewObject", None)
        if vo is not None and o.Name in look:
            c, t, vis = look[o.Name]
            vo.ShapeColor, vo.Transparency, vo.Visibility = c, t, vis


def paint(d, pred, color, transp):
    for o in d.Objects:
        vo = getattr(o, "ViewObject", None)
        if vo is not None and hasattr(vo, "ShapeColor") and pred(o.Name):
            vo.ShapeColor = color
            vo.Transparency = transp


def move(d, prefixes, vec):
    for o in solids(d):
        if starts(o.Name, prefixes):
            o.Placement = App.Placement(vec, App.Rotation())


def reset_moves(d):
    for o in solids(d):
        o.Placement = App.Placement(V(0, 0, 0), App.Rotation())


# ---------------------------------------------------------------- outputs
def hero(v, d, n=36):
    R.show_all(d)
    frames = [(AZ + 360.0 * i / n, EL) for i in range(n)]
    fs = R.sequence(v, d, frames, TMP, "hero", GW, GH)
    fs = R.crop_all(fs)
    return R.gif(fs, os.path.join(IMG, "hero.gif"), ms=90)


DETAIL_RATIO = 0.38    # new parts smaller than this fraction get a close-up


def steps(v, d, look):
    """One still per assembly step: what is already built goes grey and
    translucent, what this step adds is orange.

    Steps whose new parts are small against the whole machine also get a
    close-up, because a 40 mm bracket on a 768 mm frame is four orange pixels
    in the wide shot and tells you nothing about how it goes on.
    """
    out, details = [], {}
    R.show_all(d)
    c, height = R.centre(d), R.fit_height(v, [(AZ, EL)], pad=1.10)
    whole = R.bbox_of(d, lambda n: True)
    whole_diag = whole.DiagonalLength
    for i, (title, pre, _note) in enumerate(STEPS):
        done = [p for t, pr, _ in STEPS[:i] for p in pr]
        restore_look(d, look)
        R.visible(d, lambda n: starts(n, done + pre))
        if done:
            paint(d, lambda n: starts(n, done), DONE, 60)
        paint(d, lambda n: starts(n, pre), NEW, 0)
        R.place(v, AZ, EL, c, height)
        p = os.path.join(IMG, "step-%02d.png" % (i + 1))
        v.saveImage(p, W, H, "Current")
        out.append(p)

        bb = R.bbox_of(d, lambda n: starts(n, pre))
        if bb is not None and bb.DiagonalLength < DETAIL_RATIO * whole_diag:
            cc = V(bb.Center.x, bb.Center.y, bb.Center.z)
            # 1.9x the part's own diagonal, so it keeps enough of the frame
            # around it to show WHERE it goes, not just what it is
            dp = os.path.join(IMG, "step-%02d-detail.png" % (i + 1))
            R.place(v, AZ, EL, cc, bb.DiagonalLength * 1.9)
            v.saveImage(dp, W, H, "Current")
            details[i + 1] = dp
    restore_look(d, look)
    R.crop_all(out, margin=10)
    for p in details.values():
        R.crop_all([p], margin=10)
    return out, details


def exploded(v, d, n=18):
    """Printed parts fly out radially; conduit and hardware stay put, so the
    frame reads as a frame and you can see what clamps where."""
    R.show_all(d)
    c0 = R.centre(d)
    fly = {}
    for o in solids(d):
        if starts(o.Name, EXPLODE_FIXED):
            continue
        b = o.Shape.BoundBox.Center
        dv = V(b.x - c0.x, b.y - c0.y, b.z - c0.z)
        if dv.Length < 1e-6:
            dv = V(0, 0, 1)
        dv.normalize()
        fly[o.Name] = dv

    def before(i):
        t = i / float(n - 1)
        amt = 115.0 * (t * t * (3 - 2 * t))        # smoothstep
        for o in solids(d):
            if o.Name in fly:
                dv = fly[o.Name]
                o.Placement = App.Placement(
                    V(dv.x * amt, dv.y * amt, dv.z * amt), App.Rotation())

    frames = [(AZ, EL)] * n
    before(n - 1)
    c = R.centre(d)
    height = R.fit_height(v, [(AZ, EL)], pad=1.06)
    fs = R.sequence(v, d, frames, TMP, "exp", GW, GH, c=c, height=height,
                    before=before)
    reset_moves(d)
    fs = R.crop_all(fs)
    return R.gif(fs, os.path.join(IMG, "exploded.gif"), ms=90, boomerang=True)


def motion(v, d, n=28):
    """The gantry sweeping X and Y while the bed steps down in Z.

    Belts are HIDDEN here. Their geometry is drawn for the parked position
    only and there is no pose-dependent belt path in the model, so animating
    the gantry with belts showing would draw them attached to nothing.
    """
    import math
    R.show_all(d)
    R.visible(d, lambda nm: not starts(nm, BELTS))
    c = R.centre(d)
    height = R.fit_height(v, [(AZ, EL)], pad=1.08)

    def before(i):
        t = 2.0 * math.pi * i / float(n)
        # near the real soft limits, so the sweep reads as the whole build
        # area rather than a twitch in the middle of it
        gx = P.X_TRAVEL_LIM * 0.95 * math.sin(t)
        gy = P.Y_TRAVEL_LIM * 0.92 * math.sin(2 * t)
        nz = -(P.BUILD_Z * 0.60) * (0.5 - 0.5 * math.cos(t))
        move(d, GANTRY_Y, V(0, gy, 0))
        move(d, CARRIAGE_X, V(gx, gy, 0))
        move(d, BED_Z, V(0, 0, nz))

    fs = R.sequence(v, d, [(AZ, EL)] * n, TMP, "mot", GW, GH, c=c,
                    height=height, before=before)
    reset_moves(d)
    fs = R.crop_all(fs)
    return R.gif(fs, os.path.join(IMG, "motion.gif"), ms=85)


def stills(v, d):
    """Static three-quarter / front / side. Not part of the default run -
    nothing in the documentation references them and an uncommitted,
    unreferenced render is just weight in the repository."""
    R.show_all(d)
    out = []
    for name, (az, el) in (("iso", (AZ, EL)), ("front", (0.0, 8.0)),
                           ("side", (90.0, 8.0))):
        c = R.centre(d)
        h = R.fit_height(v, [(az, el)], pad=1.06)
        R.place(v, az, el, c, h)
        p = os.path.join(IMG, "%s.png" % name)
        v.saveImage(p, W, H, "Current")
        out.append(p)
    return R.crop_all(out, margin=10)


def main(do=("check", "steps", "hero", "exploded", "motion")):
    d = doc()
    for p in (IMG, TMP):
        if not os.path.isdir(p):
            os.makedirs(p)
    bad = check_steps(d)
    if bad:
        for b in bad:
            print("  STEP COVERAGE: %s" % b)
        raise SystemExit("assembly steps do not cover the model")
    print("  steps      ok   %d steps, every object claimed exactly once"
          % len(STEPS))
    v = R.view()
    look = save_look(d)
    try:
        if "stills" in do:
            print("  stills     ok   %d" % len(stills(v, d)))
        if "steps" in do:
            ss, dd = steps(v, d, look)
            print("  step imgs  ok   %d wide + %d close-up" % (len(ss), len(dd)))
        if "hero" in do:
            print("  hero.gif   ok   %d KB" % (hero(v, d)[1] // 1024))
        if "exploded" in do:
            print("  exploded   ok   %d KB" % (exploded(v, d)[1] // 1024))
        if "motion" in do:
            print("  motion.gif ok   %d KB" % (motion(v, d)[1] // 1024))
    finally:
        restore_look(d, look)
        reset_moves(d)
    return 0
