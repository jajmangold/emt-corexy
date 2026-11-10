# -*- coding: utf-8 -*-
"""True solid interference check on the built document.

collide.py checks the DESIGN (boxes, swept poses). This checks the MODEL: it
asks OpenCASCADE whether the solids actually overlap. Running common() on all
pairs would be thousands of booleans and would kill the instance, so pairs are
pre-filtered with optimalBoundingBox (BoundBox over-reports on splines -
freecad-boundbox-is-loose) and only genuine AABB overlaps get a boolean.
"""
import itertools
import FreeCAD as App

# Prefix pairs that are MEANT to touch: joints gripping conduit, bearings on
# rod, nuts on screws, belts on pulleys, sub-assemblies of one toolhead.
ALLOW = [
    ("Post_", ("Joint4_", "Foot_", "TeeZTop_", "YRodBlock_", "CornerTower_",
               "Gusset_")),
    ("Brace_", ("Gusset_", "Post_")),
    ("Gusset_", ("Brace_", "Post_", "Joint4_", "TeeZTop_")),
    ("RailX_", ("Joint4_", "TeeZCross_", "ZMotorMount_")),
    ("RailY_", ("Joint4_", "TeeZCross_", "TeeZTop_", "ZRodTop_")),
    ("ZRod_", ("ZMotorMount_", "ZRodTop_", "BedCarriage_")),
    # the T8 screw passes through clearance bores in both of these
    ("ZScrew_", ("ZCoupler_", "BedCarriage_", "ZMotorMount_", "ZRodTop_")),
    ("ZCoupler_", ("ZMotorMount_",)),
    ("CornerTower_", ("MotorA", "MotorB", "PulleyA", "PulleyB",
                      "IdlerA_rear", "IdlerB_rear", "Post_")),
    ("ZCoupler_", ("ZMotor_",)),
    ("ZMotor_", ("ZMotorMount_",)),
    ("YRod_", ("YCarriage_", "YRodBlock_")),
    ("XBeam_2020", ("YCarriage_", "XCarriage", "MGN12_")),
    ("MGN12_Rail", ("MGN12_Block", "YCarriage_", "XCarriage", "XBeam_2020")),
    ("MGN12_Block", ("MGN12_Rail", "XCarriage", "Stealthburner", "XBeam_2020")),
    ("Stealthburner", ("XCarriage", "MGN12_Block", "Nozzle", "ProbeMount")),
    ("XCarriage", ("Belt", "Extruder", "ProbeMount", "Hotend", "XRod_")),
    ("YCarriage_", ("YC_Idler", "Belt", "XRod_", "YRod_")),
    ("MotorA", ("HangerA", "PulleyA")),
    ("MotorB", ("HangerB", "PulleyB")),
    ("PulleyA", ("Belt", "MotorA", "HangerA")),
    ("PulleyB", ("Belt", "MotorB", "HangerB")),
    ("IdlerA_rear", ("Belt", "IdlerBracketA")),
    ("IdlerB_rear", ("Belt", "IdlerBracketB")),
    ("YC_Idler", ("Belt", "YCarriage_")),
    ("Belt", ("Belt", "Pulley", "Idler", "YC_Idler", "XCarriage", "YCarriage_")),
    ("BedPlate", ("BedSurface", "BedCarriage_")),
    ("BedSurface", ("BedPlate", "BedCarriage_", "Nozzle")),
    ("BedCarriage_", ("BedPlate", "BedSurface")),
    ("Extruder", ("XCarriage", "Extruder", "Hotend")),
    ("Hotend", ("Extruder", "Nozzle", "XCarriage")),
    ("Nozzle", ("Hotend", "BedSurface")),
    ("Probe_TLW5MC1", ("ProbeMount",)),
    ("ProbeMount", ("Probe_TLW5MC1", "XCarriage")),
    ("WipeBracket", ("RailX_wipe_m", "Brush_brass", "Joint4_wipe")),
    ("Brush_brass", ("WipeBracket", "Nozzle")),
]


def allowed(a, b):
    for pa, pbs in ALLOW:
        for pb in pbs:
            if (a.startswith(pa) and b.startswith(pb)) or \
               (a.startswith(pb) and b.startswith(pa)):
                return True
    return False


def bb_overlap(a, b, tol=-0.05):
    return not (a.XMax < b.XMin - tol or b.XMax < a.XMin - tol or
                a.YMax < b.YMin - tol or b.YMax < a.YMin - tol or
                a.ZMax < b.ZMin - tol or b.ZMax < a.ZMin - tol)


def parts(doc):
    """Only real Part features - groups must not be treated as solids."""
    return [o for o in doc.Objects
            if o.isDerivedFrom("Part::Feature")
            and getattr(o, "Shape", None) is not None and o.Shape.Solids]


def candidates(doc):
    objs = parts(doc)
    bbs = {o.Name: o.Shape.optimalBoundingBox() for o in objs}
    out = []
    for a, b in itertools.combinations(sorted(bbs), 2):
        if allowed(a, b):
            continue
        if bb_overlap(bbs[a], bbs[b]):
            out.append((a, b))
    return objs, out


def clamps_engaged(doc):
    """Every part whose job is to clamp conduit must actually engage some.

    A misplaced clamp is invisible to the overlap test, because clamp<->tube is
    on the allow-list: the 90 deg global rotation that threw two joints per
    level clean off the posts produced NO violation at all. So assert contact
    directly - and note the bore is EMT_FIT larger than the tube, so they never
    truly intersect; distToShape measures the gap without any boolean.
    """
    import params as PP
    by = {o.Name: o for o in doc.Objects if o.isDerivedFrom("Part::Feature")}
    tubes = {n: o for n, o in by.items()
             if n.startswith(("Post_", "RailX_", "RailY_", "Brace_"))}
    want = [n for n in by if n.startswith(("Joint4_", "Foot_", "TeeZTop_",
                                           "YRodBlock_", "CornerTower_",
                                           "Gusset_", "TeeZCross_",
                                           "WipeBracket"))]
    tol = PP.EMT_FIT + 0.5
    orphans = []
    for n in sorted(want):
        sh = by[n].Shape
        bb = sh.optimalBoundingBox()
        hit = 0
        for tn, to in tubes.items():
            if not bb_overlap(bb, to.Shape.optimalBoundingBox()):
                continue
            if sh.distToShape(to.Shape)[0] <= tol:
                hit += 1
        if hit == 0:
            orphans.append(n)
    return orphans


def run(doc, pairs):
    by = {o.Name: o for o in doc.Objects if hasattr(o, "Shape")}
    hits = []
    for a, b in pairs:
        try:
            v = by[a].Shape.common(by[b].Shape).Volume
        except Exception as ex:
            hits.append((a, b, "ERROR %s" % ex))
            continue
        if v > 1.0:
            hits.append((a, b, v))
    return hits
