# -*- coding: utf-8 -*-
"""Generate ASSEMBLY.md from the model. Run inside FreeCAD (build.py does it).

Every quantity here is counted off the document, including the fasteners: a
bolt hole is a cylindrical face of the right radius, so `fasteners()` finds
them by scanning each part's geometry rather than trusting a hand-kept list.
That is the only way these numbers stay true when a part changes.
"""
import io
import os

import params as P
import export
from steps import STEPS, starts

HERE = os.path.dirname(os.path.abspath(__file__))
LF = chr(10)
IMG = "docs/img"

SIZES = (("M3", P.M3), ("M4", P.M4), ("M5", P.M5))


def holes(shape, dia, tol=0.12):
    """Distinct holes of this diameter. A through-hole is often split into two
    half-cylinder faces, so faces are grouped by (axis, centre) - counting
    faces alone double-counts every hole in the machine."""
    r = dia / 2.0
    seen = set()
    for f in shape.Faces:
        s = f.Surface
        if s.__class__.__name__ != "Cylinder" or abs(s.Radius - r) > tol:
            continue
        ax, c = s.Axis, s.Center
        seen.add((round(ax.x, 2), round(ax.y, 2), round(ax.z, 2),
                  round(c.x, 1), round(c.y, 1), round(c.z, 1)))
    return len(seen)


def fasteners(doc):
    """{printed part: {"M4": n, ...}} counted from one instance of each."""
    out = {}
    for part, pred in export.INSTANCES.items():
        obj = next((o for o in doc.Objects
                    if o.isDerivedFrom("Part::Feature") and pred(o.Name)), None)
        if obj is None:
            continue
        out[part] = dict((nm, holes(obj.Shape, d)) for nm, d in SIZES)
    return out


def placed(doc):
    return [o for o in doc.Objects if o.isDerivedFrom("Part::Feature")]


def step_parts(doc, pre):
    """Printed parts added by a step: {part name: count}."""
    names = [o.Name for o in placed(doc) if starts(o.Name, pre)]
    out = {}
    for part, pred in export.INSTANCES.items():
        n = sum(1 for nm in names if pred(nm))
        if n:
            out[part] = n
    return out


def step_emt(doc, pre):
    """EMT pieces added by a step: {rounded length mm: count}."""
    out = {}
    for o in placed(doc):
        if not starts(o.Name, pre):
            continue
        if not o.Name.startswith(("Post_", "RailX", "RailY", "Brace_")):
            continue
        bb = o.Shape.BoundBox
        L = max(bb.XLength, bb.YLength, bb.ZLength)
        k = int(round(L))
        out[k] = out.get(k, 0) + 1
    return out


def build():
    import FreeCAD as App
    doc = App.getDocument("EMT_CoreXY")
    fast = fasteners(doc)

    L = []
    A = L.append
    A("# Assembly")
    A("")
    A("Thirteen steps. In every picture the part going on **now is orange** and")
    A("what is already built is grey, so you never have to work out what changed.")
    A("")
    A("![exploded view](%s/exploded.gif)" % IMG)
    A("")
    A("Everything printed and every piece of hardware, lifting off the conduit it")
    A("clamps to. The conduit itself stays put - that is the skeleton everything")
    A("else locates against.")
    A("")
    A("## Before you start")
    A("")
    A("- **Print one `Joint4_corner` and fit it to a real offcut first.** It is")
    A("  %d of the %d printed pieces; if the bore is wrong you want to find out"
      % (sum(export.SPLIT["Joint4_corner"]),
         sum(sum(v) for v in export.SPLIT.values())))
    A("  once, not %d times. Raise `EMT_FIT` in `params.py` if it is tight."
      % sum(export.SPLIT["Joint4_corner"]))
    A("- **Cut all the conduit first**, to the [cut list](README.md#emt-cut-list).")
    A("  Deburr the OUTSIDE of every cut: the clamp bore has only %.2f mm of"
      % (P.EMT_FIT / 2.0))
    A("  clearance per side, and a roll cutter leaves a raised lip.")
    A("- **Leave every clamp finger-tight until the step that says otherwise.**")
    A("  The frame has to be square before anything is locked.")
    A("- Nothing here needs a tap or a threaded insert. Every printed joint is a")
    A("  bolt through a clearance hole into a captive nut.")
    A("")

    # ---- fastener shopping list
    tot = dict((nm, 0) for nm, _ in SIZES)
    for part, counts in fast.items():
        n = sum(export.SPLIT.get(part, (0, 0)))
        for nm, _ in SIZES:
            tot[nm] += counts[nm] * n
    A("## Fasteners")
    A("")
    A("Counted off the geometry - every bolt hole in every printed part, times")
    A("how many of that part you fit:")
    A("")
    A("| Size | Qty | Mostly |")
    A("|---|---|---|")
    A("| M3 x 8-16 | %d | motor screws, the MGN12 block, the toolhead |" % tot["M3"])
    A("| M4 x 25-30 | %d | every conduit pinch clamp, one per clamp |" % tot["M4"])
    A("| M5 x 30 | %d | the belt idler studs |" % tot["M5"])
    A("")
    A("Plus a nut for each. **This is an over-estimate of a few bolts**: where two")
    A("printed parts bolt to each other, both have a clearance hole and both get")
    A("counted. Buy the round number.")
    A("")
    A("| Printed part | M3 | M4 | M5 | Fitted |")
    A("|---|---|---|---|---|")
    for part in sorted(fast, key=lambda p: -sum(export.SPLIT.get(p, (0, 0)))):
        c = fast[part]
        n = sum(export.SPLIT.get(part, (0, 0)))
        if not n:
            continue
        A("| `%s` | %s | %s | %s | x%d |"
          % (part, c["M3"] or "-", c["M4"] or "-", c["M5"] or "-", n))
    A("")

    # ---- the steps
    for i, (title, pre, note) in enumerate(STEPS, 1):
        A("## Step %d - %s" % (i, title))
        A("")
        wide = "%s/step-%02d.png" % (IMG, i)
        A("![step %d](%s)" % (i, wide))
        A("")
        det = os.path.join(HERE, "docs", "img", "step-%02d-detail.png" % i)
        if os.path.exists(det):
            A("![step %d detail](%s/step-%02d-detail.png)" % (i, IMG, i))
            A("")
        parts = step_parts(doc, pre)
        emt = step_emt(doc, pre)
        if parts:
            A("**Print:** " + ", ".join("%d x `%s`" % (n, p)
                                        for p, n in sorted(parts.items())))
            A("")
        if emt:
            A("**Conduit:** " + ", ".join("%d x %d mm" % (n, k)
                                          for k, n in sorted(emt.items(),
                                                             reverse=True)))
            A("")
        f = dict((nm, 0) for nm, _ in SIZES)
        for p, n in parts.items():
            for nm, _ in SIZES:
                f[nm] += fast.get(p, {}).get(nm, 0) * n
        if any(f.values()):
            A("**Fasteners:** " + ", ".join("%d x %s" % (f[nm], nm)
                                            for nm, _ in SIZES if f[nm]))
            A("")
        A(note)
        A("")

    A("## When it is together")
    A("")
    A("1. **Square the frame.** Measure both diagonals of the cap rectangle and")
    A("   both of the base. Equal means square. Only then tighten the braces.")
    A("2. **Check the gantry runs free** by hand over the whole of X and Y before")
    A("   the belts go on. It should coast, not grind.")
    A("3. **Level the two lead screws by hand**, motors unpowered, turning the")
    A("   couplers independently. There is no automatic tramming on this machine")
    A("   - both Z motors share one driver.")
    A("4. **Set the nozzle height** against the bed at several points and shim the")
    A("   bed mounts if the plate is bowed. A 3 mm plate of this size often is.")
    A("5. Flash Klipper, then work through the config in")
    A("   [README.md](README.md#wiring-the-skr-pico).")
    A("")
    A("Full travel is X +-%.1f and Y +-%.1f, which is larger than the %.0f x %.0f"
      % (P.X_TRAVEL_LIM, P.Y_TRAVEL_LIM, P.BUILD_X, P.BUILD_Y))
    A("print area - the extra is what the nozzle wipe station lives in.")

    out = os.path.join(HERE, "ASSEMBLY.md")
    with io.open(out, "w", encoding="utf-8", newline=LF) as f:
        f.write(LF.join(L) + LF)
    return out, len(L)
