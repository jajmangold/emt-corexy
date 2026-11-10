# -*- coding: utf-8 -*-
"""The assembly sequence: which parts go on in which order, and the one thing
worth saying about each step.

This lives apart from make_media.py so the headless documentation generator can
read it without importing FreeCADGui, and apart from the geometry so the order
can be rearranged without touching the model.

Each step claims a set of object-name prefixes. `make_media.check_steps()`
asserts that every object in the document is claimed by exactly one step, so a
mistyped prefix fails loudly rather than producing a step in which nothing
appears to change.
"""


def starts(name, prefixes):
    return any(name.startswith(p) for p in prefixes)


# (title, name prefixes, what you are actually doing)
STEPS = [
    ("Posts, feet and the bottom rectangle",
     ["Post_", "RailX_bot", "RailY_bot", "Joint4_bot", "Foot_"],
     "Thread EVERY corner clamp and foot onto the posts before you stand "
     "anything up - the bottom four, the cap four, and the four that go on "
     "later for the mid and wipe rails. They are one-piece sleeves with a "
     "pinch slot far narrower than the tube, so they will not clip on "
     "afterwards and the only way to add one is to take an end apart."),
    ("The top cap rectangle",
     ["RailX_cap", "RailY_cap", "Joint4_cap"],
     "Square the frame now, with a tape across both diagonals of the cap, "
     "before anything else is tightened."),
    ("Diagonal bracing",
     ["Brace_", "Gusset_"],
     "This is what makes the frame a frame rather than a four-bar linkage. "
     "Do not skip it and do not leave it finger-tight."),
    ("Front mid rail and the wipe rail",
     ["RailX_mid", "Joint4_mid", "RailX_wipe", "Joint4_wipe"],
     "The mid rail ties the front posts and carries the electronics; the "
     "wipe rail sits above it and carries the nozzle brush."),
    ("Z cross rails, motor mounts and motors",
     ["RailX_zcross", "TeeZCross", "ZMotorMount", "ZMotor_", "ZCoupler"],
     "Both Z motors run off ONE driver - wire them in SERIES, not parallel."),
    ("Lead screws and Z rods",
     ["ZScrew", "ZRod"],
     "The rods cantilever from the motor mounts; they only resist pitch and "
     "yaw, the screws carry the weight."),
    ("Bed carriages, mounts and the bed",
     ["BedCarriage", "BedMount", "BedPlate", "BedSurface"],
     "BedMount reaches the heatbed's OWN 240 mm holes. Never drill a new hole "
     "in an aluminium heatbed - the heater is bonded to the underside."),
    ("Y rods and their end blocks",
     ["YRodBlock", "YRod_"],
     "Both rods must end up parallel and at the same height or the gantry "
     "will bind at the extremes of Y."),
    ("A/B motors, rear idlers and the corner towers",
     ["CornerTower", "MotorA", "MotorB", "PulleyA", "PulleyB",
      "IdlerA", "IdlerB"],
     "The two motors mount in OPPOSITE senses - A shaft-down with its body "
     "above its belt plane, B shaft-up with its body below."),
    ("The gantry: Y carriages, 2020 beam and MGN12 rail",
     ["YCarriage", "XBeam_", "MGN12_Rail", "YC_Idler"],
     "Each Y carriage carries both belts' turn idlers on ONE stud, so the "
     "belt tensions apply no yaw couple."),
    ("X carriage and toolhead",
     ["MGN12_Block", "XCarriage", "Stealthburner", "Nozzle"],
     "Check this bolt pattern against your real Stealthburner before "
     "printing a second XCarriage."),
    ("Belts",
     ["BeltA", "BeltB"],
     "Both belts turn at the same point on each side, stacked in Z. Tension "
     "them equally - unequal tension racks the gantry."),
    ("Nozzle wipe and purge station",
     ["WipeBracket", "Brush_brass"],
     "Everything here stays below the nozzle, because the gantry never "
     "lifts - this machine moves the bed in Z."),
]
