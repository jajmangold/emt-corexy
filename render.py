# -*- coding: utf-8 -*-
"""Camera, visibility and image helpers for the documentation renders.

**This module needs the FreeCAD GUI.** Rendering goes through the 3D viewer,
so unlike everything else in this project it cannot run under FreeCADCmd.
`make_media.py` is the entry point; see its docstring.

The one thing worth knowing here: `fitAll()` per frame is wrong for an orbit.
It re-frames to the silhouette, and a machine that is 508 wide and 610 deep has
a silhouette that changes by ~20% as it turns, so the model visibly breathes.
Every sequence instead fits ONCE over all the frames it is about to draw, then
holds that height and orbits a fixed distance about a fixed centre.
"""
import math
import os

import FreeCAD as App
from FreeCAD import Vector as V

try:
    import FreeCADGui as Gui
    # Importing pivy is not optional even though nothing here names `coin`:
    # it loads the SWIG library behind the scene graph, and without it
    # View3DInventorPy.getCameraNode() raises "No SWIG wrapped library loaded".
    from pivy import coin                             # noqa: F401
except ImportError:                                   # headless
    Gui = None

DOCNAME = "EMT_CoreXY"
DIST = 4000.0           # orthographic, so this only has to clear the model


def view():
    Gui.ActiveDocument = Gui.getDocument(DOCNAME)
    v = Gui.ActiveDocument.ActiveView
    v.setCameraType("Orthographic")
    return v


def orientation(az, el):
    """Camera orientation for an azimuth about +Z and an elevation above the
    horizon, in degrees. az=0 looks at the FRONT of the machine (-Y face)."""
    return App.Rotation(V(0, 0, 1), az).multiply(
        App.Rotation(V(1, 0, 0), 90.0 - el))


def view_dir(az, el):
    """Unit vector the camera looks ALONG.

    Derived from the same rotation that aims the camera - a camera looks down
    its own local -Z - rather than written out as sines and cosines, which is
    how the two ended up disagreeing in Y and framing the model off-screen.
    Do NOT use View3DInventorPy.getViewDirection() to check this: it returns
    the same stale vector whatever orientation you have just set.
    """
    return orientation(az, el).multVec(V(0, 0, -1))


def visible(doc, pred):
    """Show objects whose Name satisfies pred(name); hide the rest.
    Returns how many are showing."""
    n = 0
    for o in doc.Objects:
        vo = getattr(o, "ViewObject", None)
        if vo is None:
            continue
        s = bool(pred(o.Name))
        vo.Visibility = s
        n += s
    return n


def show_all(doc):
    return visible(doc, lambda n: True)


def centre(doc, pred=None):
    """Bounding-box centre of the visible (or selected) objects."""
    bb = None
    for o in doc.Objects:
        if not o.isDerivedFrom("Part::Feature"):
            continue
        if pred is not None and not pred(o.Name):
            continue
        vo = getattr(o, "ViewObject", None)
        if pred is None and vo is not None and not vo.Visibility:
            continue
        b = o.Shape.BoundBox
        bb = b if bb is None else bb.united(b)
    if bb is None:
        return V(0, 0, 0)
    return V(bb.Center.x, bb.Center.y, bb.Center.z)


def bbox_of(doc, pred):
    bb = None
    for o in doc.Objects:
        if not o.isDerivedFrom("Part::Feature") or not pred(o.Name):
            continue
        b = o.Shape.BoundBox
        bb = b if bb is None else bb.united(b)
    return bb


def fit_height(v, frames, pad=1.06):
    """Largest orthographic height needed across `frames` [(az, el), ...], so a
    sequence can hold one framing instead of re-fitting and breathing."""
    h = 0.0
    for az, el in frames:
        v.setCameraOrientation(orientation(az, el))
        v.fitAll()
        h = max(h, v.getCameraNode().height.getValue())
    return h * pad


def place(v, az, el, c, height):
    """Point the camera at `c` from (az, el) with a fixed ortho height.

    Everything goes through the Coin camera node, including the orientation.
    View3DInventorPy.setCameraOrientation() does not take effect in time for a
    saveImage() in the same breath - mixing it with direct node writes rendered
    three of every four orbit frames empty, because the position had moved and
    the orientation had not.
    """
    cam = v.getCameraNode()
    q = orientation(az, el).Q                      # (x, y, z, w)
    cam.orientation.setValue(q[0], q[1], q[2], q[3])
    d = view_dir(az, el)
    cam.position.setValue(c.x - d.x * DIST, c.y - d.y * DIST, c.z - d.z * DIST)
    cam.height.setValue(height)
    cam.nearDistance.setValue(1.0)
    cam.farDistance.setValue(DIST * 2.5)


def shot(v, path, w, h):
    v.saveImage(path, w, h, "Current")
    return path


def sequence(v, doc, frames, outdir, stem, w, h, c=None, height=None,
             before=None):
    """Render [(az, el), ...] to <outdir>/<stem>NNN.png with fixed framing.

    `before(i)` runs per frame - that is where an animation moves parts or
    changes what is visible.
    """
    if not os.path.isdir(outdir):
        os.makedirs(outdir)
    if before is not None:
        before(0)
    if c is None:
        c = centre(doc)
    if height is None:
        height = fit_height(v, frames)
    out = []
    for i, (az, el) in enumerate(frames):
        if before is not None:
            before(i)
        place(v, az, el, c, height)
        p = os.path.join(outdir, "%s%03d.png" % (stem, i))
        v.saveImage(p, w, h, "Current")
        out.append(p)
    return out


def crop_all(frames, margin=8):
    """Crop every frame to ONE box: the union of the content across all of
    them. Per-frame cropping would make the model jump around; this just
    removes the dead background a fitAll leaves on a tall model in a wide
    frame, which is most of the file size of a GIF."""
    from PIL import Image, ImageChops
    ims = [Image.open(f).convert("RGB") for f in frames]
    bg = ims[0].getpixel((0, 0))
    box = None
    for im in ims:
        diff = ImageChops.difference(im, Image.new("RGB", im.size, bg))
        b = diff.getbbox()
        if b is None:
            continue
        box = b if box is None else (min(box[0], b[0]), min(box[1], b[1]),
                                     max(box[2], b[2]), max(box[3], b[3]))
    if box is None:
        return frames
    w, h = ims[0].size
    box = (max(0, box[0] - margin), max(0, box[1] - margin),
           min(w, box[2] + margin), min(h, box[3] + margin))
    for im, f in zip(ims, frames):
        im.crop(box).save(f)
    return frames


# ------------------------------------------------------------------ GIF
def gif(frames, path, ms=80, colors=96, loop=0, boomerang=False):
    """Write an animated GIF. Quantising every frame against ONE palette built
    from the whole sequence stops the background shimmering between frames."""
    from PIL import Image
    ims = [Image.open(f).convert("RGB") for f in frames]
    if boomerang:
        ims = ims + ims[-2:0:-1]
    w, h = ims[0].size
    strip = Image.new("RGB", (w, h * len(ims)))
    for i, im in enumerate(ims):
        strip.paste(im, (0, i * h))
    pal = strip.quantize(colors=colors, method=Image.MEDIANCUT)
    qs = [im.quantize(palette=pal, dither=Image.NONE) for im in ims]
    qs[0].save(path, save_all=True, append_images=qs[1:], duration=ms,
               loop=loop, optimize=True, disposal=2)
    return path, os.path.getsize(path)
