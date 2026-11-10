# -*- coding: utf-8 -*-
"""STL export with mesh validation.

Never write a mesh without checking it. A solid can be perfect while its
tessellation is open - OpenCASCADE turns a tangency into a non-manifold mesh,
the STL exports with boundary edges, and a slicer silently patches it into
something nobody chose (freecad-tangent-non-manifold). Two arithmetic tests
catch it: a closed triangle mesh has exactly 3F/2 edges, and its volume must
agree with the solid.
"""
import os
import FreeCAD as App
import Mesh
import MeshPart

import params as P
import stages as S1
import stages2 as S2

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stl")

# name -> (builder, quantity, note)
PARTS = [
    ("Joint4_corner",  S1.joint4_shape,      18, "frame corner, all 4 levels + wipe rail"),
    ("FootPad",        S1.foot_shape,         4, "post feet"),
    ("TeeZCross",      S1.tee_zcross_shape,   4, "Z-motor cross rail tees"),
    ("ZMotorMount",    S1.zmotor_mount_shape, 2, "Z motor + 2 rod feet"),
    ("BedCarriage",    S1.bed_carriage_shape, 2, "LM10UU x2 + T8 nut"),
    ("BedMount",       S1.bed_mount_shape,    4, "carriage -> the bed's own 240 mm holes"),
    ("WipeBracket",    S1.wipe_bracket_shape, 1, "nozzle brush + purge station"),
    ("YRodBlock",      S2.yrod_block_shape,   4, "Y rod ends"),
    ("YCarriage",      S2.y_carriage_shape,   2, "mirror for the second one"),
    ("XCarriage",      S2.x_carriage_shape,   1, "toolhead carriage"),
    ("CornerTower_R",  lambda: S2.corner_tower_shape(False), 1, "rear-right: B motor low"),
    ("CornerTower_L",  lambda: S2.corner_tower_shape(True),  1, "rear-left: A motor high"),
    # brace gussets: the two ends of a diagonal are different parts, and the
    # two side braces (and the two cap braces) are mirror/rotation pairs
    ("Gusset_side_low",
     lambda: S1.gusset_for("Brace_side_p", 0), 2, "side diagonal, bottom end"),
    ("Gusset_side_high",
     lambda: S1.gusset_for("Brace_side_p", 1), 2, "side diagonal, top end"),
    ("Gusset_rear_low",
     lambda: S1.gusset_for("Brace_rear", 0), 1, "rear diagonal, bottom end"),
    ("Gusset_rear_high",
     lambda: S1.gusset_for("Brace_rear", 1), 1, "rear diagonal, top end"),
    ("Gusset_cap_a",
     lambda: S1.gusset_for("Brace_cap_pp", 0), 2, "cap plan brace, X-rail end"),
    ("Gusset_cap_b",
     lambda: S1.gusset_for("Brace_cap_pp", 1), 2, "cap plan brace, Y-rail end"),
]


# How many of each part are the DIRECT chirality and how many are the MIRROR.
# Read straight off the generating code in stages*.py: an instance placed with
# rotz()/translate() is the same part, one placed with mir_x()/mir_y() is the
# opposite hand. Both chiralities get their own STL so nothing depends on
# remembering to flip a part in the slicer.
SPLIT = {
    "Joint4_corner":      (18, 0),   # place_corner() is rotation-only
    "FootPad":            (4, 0),
    "TeeZCross":          (2, 2),
    "ZMotorMount":        (1, 1),
    "BedCarriage":        (1, 1),
    "BedMount":           (2, 2),
    "WipeBracket":        (1, 0),
    "YRodBlock":          (2, 2),
    "YCarriage":          (1, 1),
    "XCarriage":          (1, 0),
    "CornerTower_R":      (1, 0),
    "CornerTower_L":      (0, 1),    # placed as mir_x of the Aup shape
    "Gusset_side_low":    (1, 1),
    "Gusset_side_high":   (1, 1),
    "Gusset_rear_low":    (1, 0),
    "Gusset_rear_high":   (1, 0),
    "Gusset_cap_a":       (2, 0),    # cap_mm is cap_pp rotated 180, same hand
    "Gusset_cap_b":       (2, 0),
}

# Which assembly stage each part belongs to, so the print can be batched in
# build order and assembly can start before everything is done.
BATCH = {
    "Joint4_corner": 1, "FootPad": 1, "TeeZCross": 1,
    "Gusset_side_low": 2, "Gusset_side_high": 2, "Gusset_rear_low": 2,
    "Gusset_rear_high": 2,
    "Gusset_cap_a": 2, "Gusset_cap_b": 2,
    "ZMotorMount": 3, "BedCarriage": 3, "BedMount": 3,
    "WipeBracket": 5,
    "YRodBlock": 4, "YCarriage": 4, "CornerTower_R": 4, "CornerTower_L": 4,
    "XCarriage": 4,
}
BATCH_NAME = {1: "Frame", 2: "Bracing", 3: "Z axis", 4: "Gantry",
              5: "Wipe station"}


def export_mirrors(write=True):
    """Write a <name>_M.stl for every part that needs the opposite hand."""
    import stages as _S1
    out = []
    for name, fn, qty, note in PARTS:
        nd, nm = SPLIT.get(name, (qty, 0))
        if nm == 0:
            continue
        sh = _S1.mir_x(fn())
        mesh = MeshPart.meshFromShape(Shape=sh, LinearDeflection=0.01,
                                      AngularDeflection=0.17, Relative=False)
        bad = validate(sh, mesh)
        if not bad and write:
            mesh.write(os.path.join(OUT, "%s_M.stl" % name))
        out.append((name + "_M", nm, sh.optimalBoundingBox(), sh.Volume,
                    mesh, bad))
    return out


def validate(shape, mesh):
    """Return a list of reasons this mesh must not be written."""
    bad = []
    if len(shape.Solids) != 1:
        bad.append("%d solids" % len(shape.Solids))
    if not shape.isValid():
        bad.append("solid invalid")
    if not shape.isClosed():
        bad.append("solid not closed")
    extra = mesh.CountEdges - 3 * mesh.CountFacets // 2
    if extra != 0:
        bad.append("mesh open: %+d edges vs 3F/2" % extra)
    if not mesh.isSolid():
        bad.append("mesh not solid")
    if mesh.hasNonManifolds():
        bad.append("non-manifold")
    if mesh.hasSelfIntersections():
        bad.append("self-intersecting")
    dv = abs(mesh.Volume - shape.Volume) / max(shape.Volume, 1e-9)
    if dv > 0.002:
        bad.append("volume off by %.2f%%" % (dv * 100))
    return bad


def export(subset=None, write=True):
    if not os.path.isdir(OUT):
        os.makedirs(OUT)
    rows = []
    for name, fn, qty, note in PARTS:
        if subset and name not in subset:
            continue
        sh = fn()
        mesh = MeshPart.meshFromShape(Shape=sh, LinearDeflection=0.01,
                                      AngularDeflection=0.17, Relative=False)
        bad = validate(sh, mesh)
        bb = sh.optimalBoundingBox()
        fits = (bb.XLength < P.PRINT_ENV[0] and bb.YLength < P.PRINT_ENV[1]
                and bb.ZLength < P.PRINT_ENV[2])
        if not fits:
            bad.append("exceeds %.0fx%.0fx%.0f print envelope" % P.PRINT_ENV)
        # Only write the direct file if any are actually printed that hand.
        # CornerTower_L is placed as mir_x of this shape, so SPLIT is (0, 1) -
        # writing CornerTower_L.stl hands you the wrong-hand part.
        nd, _nm = SPLIT.get(name, (qty, 0))
        path = os.path.join(OUT, "%s.stl" % name)
        if not bad and write and nd:
            mesh.write(path)
        elif not nd and os.path.exists(path):
            os.remove(path)
        rows.append((name, qty, bb, sh.Volume, mesh, bad))
    return rows
