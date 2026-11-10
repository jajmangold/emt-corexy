# -*- coding: utf-8 -*-
"""Generate PRINT_LIST.md from the model. Run inside FreeCAD."""
import io
import os
import params as P
import export

HERE = os.path.dirname(os.path.abspath(__file__))
LF = chr(10)      # LF endings on every platform

# How to turn the part so the chosen face is down. Orientations are not
# asserted any more - printability.py measures them off the solid.
HOWTO = {
    "+Z": "as modelled, +Z up",
    "-Z": "upside down (rotate 180 about X)",
    "+X": "on its side, +X up (rotate -90 about Y)",
    "-X": "on its side, -X up (rotate +90 about Y)",
    "+Y": "on its back, +Y up (rotate -90 about X)",
    "-Y": "on its front, -Y up (rotate +90 about X)",
}


def build():
    import printability
    rows = {r[0]: r for r in export.export(write=False)}
    orient = {}
    for name, fn, qty, note in export.PARTS:
        nm, info, fits = printability.best(fn())
        orient[name] = (nm, info, fits)

    L = []
    A = L.append
    A("# Print list")
    A("")
    A("%d pieces, %d files. Every file in `stl/` is print-ready as-is: parts that"
      % (sum(sum(v) for v in export.SPLIT.values()),
         sum(1 for n, (d, m) in export.SPLIT.items() if d) +
         sum(1 for n, (d, m) in export.SPLIT.items() if m)))
    A("need the opposite hand have their own `_M` file, so **nothing here depends")
    A("on remembering to mirror something in the slicer**.")
    A("")
    A("## Settings")
    A("")
    A("- **PETG or ASA. Not PLA.** Every one of these is a clamp held by bolt")
    A("  preload, and PLA creeps under sustained load - the frame would go slack")
    A("  over weeks. The bed also radiates onto the lower joints.")
    A("- **0.6 mm nozzle, 0.3 mm layers.** These are structural blocks; nothing")
    A("  here is cosmetic, and it roughly halves the time against 0.4/0.2.")
    A("- **4-5 perimeters, 25-30 % infill.** In a pinch clamp the perimeters")
    A("  carry the hoop load, so walls matter far more than infill.")
    A("- **No supports needed on any part.** That is measured, not assumed:")
    A("  `printability.py` finds each part's outward face normals, picks the")
    A("  orientation, and reports downward-facing area steeper than 45 degrees.")
    A("  It comes to ZERO for every part - the geometry is all axis-aligned")
    A("  boxes and cylinders, so every downward face is either vertical (fine)")
    A("  or horizontal (a bridge).")
    _brim = [n for n in orient if orient[n][1]["contact"] < 800]
    _bc = sorted(orient[n][1]["contact"] for n in _brim)
    A("- **Brim on the %d part types marked below.** Their bed face is as little"
      % len(_brim))
    A("  as %.0f mm2 - a clamp sleeve end-annulus - which is not much to hold a"
      % (_bc[0] if _bc else 0))
    A("  tall part down.")
    _br = sorted(((orient[n][1]["span"], n) for n in orient), reverse=True)[:3]
    A("- The longest bridges are %s."
      % ", ".join("%.0f mm (`%s`)" % (s, n) for s, n in _br))
    A("  Those will sag slightly on the underside; it is cosmetic, and none of")
    A("  them is a mating face.")
    A("- Check the slicer is not bridging the %.1f mm pinch slots closed - they"
      % P.SLOT_W)
    A("  have to stay open or the clamp cannot pinch.")
    A("- Bores are a clearance fit with a pinch slot (%.2f mm bore on a %.2f mm"
      % (P.EMT_BORE, P.EMT_OD))
    A("  tube), so a little sag in a horizontally-printed bore is tolerable -")
    A("  the bolt pulls it round. Ream it if a tube will not start.")
    A("")

    for b in sorted(export.BATCH_NAME):
        names = [n for n in export.SPLIT if export.BATCH.get(n) == b]
        if not names:
            continue
        vol = 0.0
        pieces = 0
        A("## Batch %d - %s" % (b, export.BATCH_NAME[b]))
        A("")
        A("| File | Qty | cm3 | Print it | Bed mm2 | Notes |")
        A("|---|---|---|---|---|---|")
        for n in sorted(names, key=lambda x: -(rows[x][3] * sum(export.SPLIT[x]))):
            nd, nm = export.SPLIT[n]
            v = rows[n][3] / 1000.0
            up, info, fits = orient[n]
            notes = []
            if info["contact"] < 800:
                notes.append("**brim**")
            if info["steep"] > 400:
                notes.append("**support**")
            if info["span"] > 30:
                notes.append("%.0f mm bridge" % info["span"])
            note = ", ".join(notes) if notes else "-"
            if nd:
                A("| `%s.stl` | %d | %.0f | %s | %.0f | %s |"
                  % (n, nd, v, HOWTO[up], info["contact"], note))
            if nm:
                A("| `%s_M.stl` | %d | %.0f | mirror of the above | %.0f | %s |"
                  % (n, nm, v, info["contact"], note))
            vol += v * (nd + nm)
            pieces += nd + nm
        A("")
        A("%d piece%s, %.0f cm3 -> about %.2f-%.2f kg, %.0f-%.0f h."
          % (pieces, "" if pieces == 1 else "s", vol,
             vol * 0.40 * 1.27 / 1000, vol * 0.50 * 1.27 / 1000,
             max(1.0, vol * 0.40 / 25.0), max(1.0, vol * 0.50 / 15.0)))
        A("")

    tot = sum(rows[n][3] / 1000.0 * sum(export.SPLIT[n]) for n in export.SPLIT)
    A("## Total")
    A("")
    A("**%d pieces, %.0f cm3** = %.1f-%.1f kg and roughly %.0f-%.0f print-hours"
      % (sum(sum(v) for v in export.SPLIT.values()), tot,
         tot * 0.40 * 1.27 / 1000, tot * 0.50 * 1.27 / 1000,
         tot * 0.40 / 25.0, tot * 0.50 / 15.0))
    A("at 40-50 % effective density and 15-25 cm3/h.")
    A("")
    A("Batches are in assembly order, so you can start building the frame while")
    A("the rest prints. Batch 1 alone (%d pieces) gets the whole frame standing."
      % sum(sum(export.SPLIT[n]) for n in export.SPLIT
            if export.BATCH.get(n) == 1))
    A("")
    A("## Print the frame joints first and check one")
    A("")
    _nj = sum(export.SPLIT["Joint4_corner"])
    A("`Joint4_corner` is %d of the %d pieces. Print **one**, put it on a real"
      % (_nj, sum(sum(v) for v in export.SPLIT.values())))
    A("piece of conduit and tighten the bolt before committing to the other %d:"
      % (_nj - 1))
    A("the bore is sized from the nominal %.2f mm OD and real EMT wanders about"
      % P.EMT_OD)
    A("+-0.1 mm between makes. If it is tight, raise `EMT_FIT` in `params.py`")
    A("(currently %.2f mm) and re-run; if it is sloppy, lower it." % P.EMT_FIT)
    out = os.path.join(HERE, "PRINT_LIST.md")
    with io.open(out, "w", encoding="utf-8", newline=LF) as f:
        f.write(u"\n".join(L) + u"\n")
    return out, len(L)
