# -*- coding: utf-8 -*-
"""Rebuild the whole machine, verify it, and write every output. One command.

    FreeCADCmd build.py                        # model, checks, STLs, docs
    FreeCADCmd build.py --pass --no-write      # checks only, writes nothing

(`--pass` is FreeCAD's own flag for "stop parsing, hand the rest to the
script"; without it FreeCAD claims the argument and prints its help instead.)

It also runs inside the GUI - paste into the Python console:

    import build; build.main()

Nothing in this project is drawn by hand and no number in the documentation is
typed twice: `params.py` is the only place a dimension exists, the model is
generated from it, and README.md / PRINT_LIST.md are generated from the model.
So the way to change this printer is to edit `params.py` and run this file.

It will REFUSE to write STLs if any check fails. That is the point - every
fault this project has had was a silent one (a mirrored part stacked on its
twin, a rod embedded in a solid pad, a mesh that exported open), and each was
caught by one of the five checks below rather than by looking at the model.
"""
import os
import sys
import time


def say(msg=""):
    """print, flushed. FreeCADCmd exits without flushing Python's stdout, so
    `FreeCADCmd build.py > log` silently loses the END of the report - which is
    the part that says whether it worked."""
    print(msg, flush=True)


HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import FreeCAD as App                                       # noqa: E402

# Note: OCCT's mesh and topology checks print their own percent-counter to
# stdout and it interleaves with the report below. There is no way to turn it
# off from Python (ConfigSet("ProgressIndicator", ...) does nothing), so the
# report is printed flushed and line-by-line and you read around the noise.

import params as P                                          # noqa: E402
import geom                                                  # noqa: E402
import stages as S1                                          # noqa: E402
import stages2 as S2                                         # noqa: E402
import collide                                               # noqa: E402
import interfere                                             # noqa: E402
import export                                                # noqa: E402

# In assembly order, which is also the order the print batches are numbered in.
STAGES = [
    ("frame      EMT posts, rails and diagonals", S1.stage_frame),
    ("joints     printed pinch clamps + feet", S1.stage_joints),
    ("braces     diagonal gussets", S1.stage_braces),
    ("z_hw       leadscrews, rods, motors, bed", S1.stage_z_hardware),
    ("z_printed  motor mounts, carriages, bed mounts", S1.stage_z_printed),
    ("gantry_hw  2020 + MGN12, A/B motors, belts", S2.stage_gantry_hardware),
    ("gantry_pr  Y carriages, X carriage, towers", S2.stage_gantry_printed),
    ("toolhead   Stealthburner envelope", S2.stage_toolhead),
]


def build():
    """Draw every stage into a clean document."""
    d = geom.doc()
    geom.clear()
    for label, fn in STAGES:
        fn()
    d.recompute()
    return d


def verify(d):
    """Five independent checks. Returns (ok, lines)."""
    out = []
    ok = True

    errs = P.check()
    out.append(("params", "PASS" if not errs else "; ".join(errs), not errs))
    ok = ok and not errs

    worst, bad = collide.run(7, 7, 5)
    msg = "%d pairs over 441 poses, %d violations" % (len(worst), len(bad))
    if bad:
        msg += ": " + "; ".join("%s<->%s %.2f" % (a, b, v)
                                for (a, b), v in sorted(bad.items())[:5])
    out.append(("collide", msg, not bad))
    ok = ok and not bad

    objs, pairs = interfere.candidates(d)
    hits = interfere.run(d, pairs)
    out.append(("interference",
                "%d parts, %d candidate pairs, %d solid overlaps"
                % (len(objs), len(pairs), len(hits)), not hits))
    ok = ok and not hits

    orph = interfere.clamps_engaged(d)
    out.append(("clamps engaged",
                "all engaged" if not orph else "ORPHANS: " + ", ".join(orph),
                not orph))
    ok = ok and not orph

    return ok, out


def main(write=True, save=True, docs=True):
    t0 = time.time()
    say("=" * 68)
    d = build()
    say("model: %d objects" % len(d.Objects))

    ok, rows = verify(d)
    say("-" * 68)
    for name, msg, good in rows:
        say("  %-14s %-4s %s" % (name, "ok" if good else "FAIL", msg))
    say("-" * 68)

    if not ok:
        say("CHECKS FAILED - nothing written.")
        return 1

    rows = export.export(write=write) + export.export_mirrors(write=write)
    bad = [(r[0], r[5]) for r in rows if r[5]]
    for name, why in bad:
        say("  mesh FAIL %-18s %s" % (name, "; ".join(why)))
    if bad:
        say("MESH VALIDATION FAILED - no STL written.")
        return 1
    nwrote = len([f for f in os.listdir(export.OUT) if f.endswith(".stl")])
    say("  %-14s ok   %d solids valid, %d STL files in stl/"
      % ("meshes", len(rows), nwrote))

    if docs and write:
        import gen_readme
        import gen_printlist
        for mod in (gen_readme, gen_printlist):
            path, n = mod.build()
            say("  %-14s ok   %s (%d lines)"
                  % ("docs", os.path.basename(path), n))

    if save:
        d.save() if d.FileName else d.saveAs(
            os.path.join(HERE, "EMT_CoreXY.FCStd"))
        say("  %-14s ok   %s" % ("saved", os.path.basename(d.FileName)))

    vol = sum(r[3] / 1000.0 * sum(export.SPLIT.get(r[0], (r[1], 0)))
              for r in rows if not r[0].endswith("_M"))
    say("=" * 68)
    say("%d printed pieces, %d EMT cuts, %.0f cm3 of filament, %.1f s"
          % (sum(sum(v) for v in export.SPLIT.values()),
             sum(q for _n, q, _L in P.cutlist()), vol, time.time() - t0))
    return 0


# FreeCADCmd does not exec a script as __main__ - it IMPORTS it under a module
# name taken from the filename, so a plain `__name__ == "__main__"` guard never
# fires and the script silently does nothing at all.
if __name__ in ("__main__", "build"):
    _w = "--no-write" not in sys.argv
    _rc = main(write=_w, save=_w, docs=_w)
    if __name__ == "__main__":
        sys.exit(_rc)
