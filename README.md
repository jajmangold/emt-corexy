# EMT CoreXY - 300 x 300 x 400 mm

A large CoreXY printer whose **frame is nothing but 1/2 inch EMT electrical
conduit**; every joint, bearing block and bracket is printed. All motion runs
on hardened linear rod. Controller is a BTT SKR Pico.

**Print-ready STLs are in [`stl/`](stl/); what to print and how is in
[PRINT_LIST.md](PRINT_LIST.md).** If you only want to build the machine,
those two and this file are all you need - skip to
[the cut list](#emt-cut-list).

## Build it from source

The whole machine is generated. One command redraws it, re-runs every
check, re-exports all 26 STLs and regenerates this file and the print list:

```sh
FreeCADCmd build.py                    # ~60 s, no GUI needed
FreeCADCmd build.py --pass --no-write  # just the checks, writes nothing
```

(FreeCAD's mesh checker prints its own percent-counter over the top of the
report and it cannot be turned off from Python; the report lines are the
ones starting with two spaces. It ends with a pass/fail summary.)

It **refuses to write any STL if a check fails**, which is the point: every
fault this design has had was a silent one - a mirrored part stacked exactly
on its twin, a 10 mm rod embedded in a solid pad, a mesh that exported open
and got patched by the slicer. None was visible in the viewport; each was
caught by one of the checks below.

| File | What it is |
|---|---|
| `params.py` | **Every dimension in the machine.** Nothing is dimensioned anywhere else. Also `check()`, the 1-D invariants. |
| `geom.py` | Primitives, and the one pinch-clamp function every joint is made from. |
| `stages.py` | Frame, printed joints, bracing, Z axis, bed. |
| `stages2.py` | Gantry, belts, carriages, toolhead. |
| `collide.py` | Pose-sampled box-overlap check over 441 machine poses. |
| `interfere.py` | Real boolean intersection of every candidate pair, plus the positive "every clamp is actually on its tube" assertion. |
| `printability.py` | Measures each part's face normals to pick a print orientation and find unsupported overhang. |
| `export.py` | STL export with mesh validation. |
| `gen_readme.py`, `gen_printlist.py` | Generate this file and PRINT_LIST.md from the model. |
| `build.py` | Runs all of the above. |

`EMT_CoreXY.FCStd` is **not** in the repository: it is generated, and every
save rewrites timestamps inside it, so it would show as a 1.3 MB binary diff
on every rebuild. Run `build.py` once and you have it. The STLs and these
two Markdown files *are* committed, because they regenerate byte-for-byte -
so a pull request that changes a dimension shows exactly which parts moved.

**To change the printer, edit `params.py` and re-run `build.py`.** No
dimension appears in two places and no number in this document was typed
by hand, so a changed parameter propagates to the geometry, the checks, the
STLs, the cut list and the print list at once.

## Numbers

| | |
|---|---|
| Build volume | 300 x 300 x 400 mm |
| Outer envelope | 508 W x 568 D x 768 H mm |
| X / Y travel available | +-163.3 / +-182.0 mm |
| Bed | 310 mm square, print surface travels Z 108..508 |
| Conduit | 1/2 in EMT, 17.93 mm OD, 1.07 mm wall |
| EMT needed | 11576 mm = 38.0 ft = 4 x 10 ft stick |
| Printed plastic | 3266 cm3 of solid volume across 18 part types |

The frame is deeper than it is wide (550 vs 490 between post centres).
That is not styling: the A/B motors have to sit behind the Y-carriage sweep,
and that is the room it takes.

## The three decisions that shaped it

**1. The SKR Pico has four drivers, not five.** It exposes five motor
connectors - X, Y, Z1, Z2, E - but Z1 and Z2 are paralleled onto a single
TMC2209 on the board. So the machine is X=A, Y=B, Z=both screws, E=extruder,
and **there is no independent Z**: no G34, no automatic gantry/bed tramming.
The two lead screws get levelled mechanically, once, and the probe is for
`bed_mesh` only. Your fifth 2 A NEMA 17 is a spare.

**2. Both belts turn at the same (X,Y) on each side, stacked in Z.** One idler
stud per Y carriage carries both belts; each rear corner is one coaxial
station with a motor and the other belt's idler sharing an axis. Both beam
runs also share Y=25, so the two belt tensions apply no yaw couple to the
carriage. Because the corners are coaxial, the two motors must mount in
opposite senses to stay out of each other's way:

| Belt | Plane | Motor | Body | Corner |
|---|---|---|---|---|
| A | Z=592 | shaft **down** | above, 606..654 | rear-left |
| B | Z=526 | shaft **up** | below, 464..512 | rear-right |

**3. The toolhead needs 51 mm below the rails, not 60.** A 42 mm NEMA 17
is what a Voron Stealthburner + Clockwork 2.5 is built around, and it also
fixes the rod slop: two LM12UU on round rod turn 0.02-0.05 mm of bearing
play into 0.08-0.19 mm of nozzle wander, while an MGN12H block is
preloaded. TOOL_DROP is therefore 50.91 mm - MEASURED off the official Voron
CAD, not guessed - and because the toolhead hangs forward of the beam the
whole bed / Z subsystem shifts forward by BED_Y (-52.10) so the nozzle still
sweeps the bed symmetrically.

## Bracing - why diagonals, not mid rails

A rectangle of tube on pinch clamps is a four-bar mechanism. Its racking
stiffness comes only from joint ROTATIONAL stiffness, which is exactly what
a clamp on round tube is worst at. For one 550 x 440 side bay:

| | lateral stiffness | vs unbraced |
|---|---|---|
| unbraced, **ideal rigid corners** | 55 N/mm | 1x |
| + a mid rail (two storeys) | 221 N/mm | 4x |
| one diagonal, axial | **7090 N/mm** | **128x** |

The diagonal is 32x the mid rail, and that understates it: the 55 and 221
figures assume rigid corners, while the diagonal's 7090 N/mm is axial and
does not care about joint rigidity at all. Post buckling - the usual excuse
for a mid rectangle - is not a failure mode here either: Euler critical load
for a 768 mm post is 6113 N and it carries about 49 N, a factor of 125.

So the mid rectangle is gone, replaced by six diagonals. Only the FRONT mid
rail is kept, as a post tie and electronics shelf, leaving the front face
open for access.

| Brace | Plane | Span | Anchored to |
|---|---|---|---|
| `side_m` | side | 715 mm | posts |
| `side_p` | side | 715 mm | posts |
| `rear` | rear | 783 mm | rails |
| `cap_mm` | cap | 199 mm | rails |
| `cap_pp` | cap | 199 mm | rails |

Two things forced the layout. **Rail-anchored braces are offset 20.9 mm out
of the rail plane** - a brace whose endpoint lies on a rail axis runs
straight through that rail, and a bare one-diameter offset leaves the two
tubes exactly tangent. And **the side planes cannot be braced above the
gantry at all**: the Y carriages sweep X 232..264 at Z 662..694 in precisely
those planes. Upper-region shear is taken by the rear diagonal and the two
cap plan braces instead; if you want more, a bolted side PANEL is the answer
there, and it is the enclosure anyway.

## EMT cut list

| Qty | Length | What |
|---|---|---|
| 4 | 768 mm | post |
| 8 | 471 mm | rail along X: bottom x2, cap x2, front mid, front wipe, 2 Z-motor cross |
| 4 | 531 mm | rail along Y: bottom x2, cap x2 |
| 1 | 715 mm | Brace side m |
| 1 | 715 mm | Brace side p |
| 1 | 783 mm | Brace rear |
| 1 | 199 mm | Brace cap mm |
| 1 | 199 mm | Brace cap pp |

### Nesting into 10 ft sticks

38.0 ft of conduit out of 4 x 10 ft of stock leaves only 616 mm of total
slack, so it does nest - but not in an arbitrary order. First-fit on the
longest pieces first:

| Stick | Cuts | Used | Left |
|---|---|---|---|
| 1 | 783 + 768 + 768 + 715 | 3034 mm | 14 mm |
| 2 | 768 + 768 + 715 + 531 + 199 | 2981 mm | 67 mm |
| 3 | 531 + 531 + 531 + 471 + 471 + 471 | 3006 mm | 42 mm |
| 4 | 471 + 471 + 471 + 471 + 471 + 199 | 2554 mm | 494 mm |

A clamping/roller cutter removes no material, so there is no kerf to
budget - but it does swage about 2 mm of each end inward. That is fine for
a clamp bore and bad for a butt face, so **deburr and re-round the ends of
the rails**, which are the only pieces that bear end-to-end.

### Which cuts actually matter

**Only the 12 rails are length-critical.** Each one butts at BOTH ends -
against posts, or against the two tees on the Z cross rails - so its
length sets the frame. Cut to **471 mm** and **531 mm**, erring
short rather than long: a long rail just spreads the posts slightly, but
it is the pair of rails at a shared corner that runs out of room first -
they clear each other by only 0.5 mm.

**The 4 posts and 6 diagonals are length-forgiving.** Every one of their
ends lands in a clamp, not a socket, so a few millimetres either way only
changes where the clamp ends up sitting. Do not chase the 657.6 / 671.2 /
199.1 figures - round them to the nearest millimetre and move on. This is
the one real advantage of clamping over socketing.

**Deburr the OUTSIDE edge of every cut.** The collar bore is 18.38 mm
against a 17.93 mm tube: that is 0.23 mm of clearance per side and nothing
more. A raised lip will stop the collar going on.

**A roll/wheel-type cutter swages the end inward.** That is harmless for
the collar fit - it shrinks the lip if anything - but it rounds off the
bearing face, so if you want the closed butt to actually carry compression,
finish the end flat with a file or a chop saw. The frame does not depend on
it: the collar carries the load on friction either way (~1.9 kN of grip
from one M4 against member loads of tens of newtons). The butt is there to
remove slop and add a direct compression path, not to make the joint work.

The joints are **pinch
clamps, not interference sockets** - real EMT OD wanders about +-0.1 mm and a
fixed bore would be either loose or unassemblable. Bore is 18.38 mm
(0.45 over nominal); the M4 pinch bolt takes up the rest.

## Printed parts

| Part | Qty | Size mm | cm3 ea | Notes |
|---|---|---|---|---|
| `Joint4_corner` | 18 | 59 x 59 x 44 | 36 | frame corner, all 4 levels + wipe rail |
| `FootPad` | 4 | 56 x 56 x 45 | 38 | post feet |
| `TeeZCross` | 4 | 43 x 38 x 38 | 23 | Z-motor cross rail tees |
| `ZMotorMount` | 2 | 38 x 147 x 62 | 104 | Z motor + 2 rod feet |
| `BedCarriage` | 2 | 63 x 142 x 58 | 221 | LM10UU x2 + T8 nut |
| `BedMount` | 4 | 55 x 88 x 28 | 52 | carriage -> the bed's own 240 mm holes |
| `WipeBracket` | 1 | 48 x 79 x 66 | 46 | nozzle brush + purge station |
| `YRodBlock` | 4 | 37 x 52 x 38 | 22 | Y rod ends |
| `YCarriage` | 2 | 73 x 96 x 147 | 164 | mirror for the second one |
| `XCarriage` | 1 | 58 x 64 x 92 | 202 | toolhead carriage |
| `CornerTower_R` | 1 | 96 x 91 x 104 | 200 | rear-right: B motor low |
| `CornerTower_L` | 1 | 96 x 91 x 100 | 193 | rear-left: A motor high |
| `Gusset_side_low` | 2 | 38 x 69 x 48 | 43 | side diagonal, bottom end |
| `Gusset_side_high` | 2 | 38 x 69 x 48 | 43 | side diagonal, top end |
| `Gusset_rear_low` | 1 | 42 x 59 x 50 | 48 | rear diagonal, bottom end |
| `Gusset_rear_high` | 1 | 42 x 59 x 50 | 48 | rear diagonal, top end |
| `Gusset_cap_a` | 2 | 46 x 49 x 59 | 49 | cap plan brace, X-rail end |
| `Gusset_cap_b` | 2 | 46 x 49 x 59 | 48 | cap plan brace, Y-rail end |

All fit a 245 mm cube, so they print on the Q1 Pro. STLs in `stl/`.
Every one was checked as a single closed valid solid, and every mesh was
verified watertight (edges == 3F/2) with its volume within 0.2 % of the
solid before being written - an open STL gets silently patched by a slicer.

`YCarriage`, `BedCarriage`, `ZMotorMount` and `BedMount` are mirrored:
print one as-is and one mirrored. `Joint4_corner` is one part for all 16
frame corners.

## Material efficiency

The first version of this design used **5481 cm3** of plastic. It now uses
**3266 cm3, a 40 % reduction**, with no loss of function - every part is
still a single closed solid and the full clearance set still verifies.
Three changes did it.

**1. The clamp was the wrong shape.** Everything that grips conduit goes
through one function, `geom.clamp_parts()`, and it was a solid rectangular
block: of a 39 x 29 x 46 block only **36 % was the load-bearing annulus**
and 64 % was corner material carrying nothing. Maker Pipe and every shaft
collar use a thin sleeve with a single bolt lug, so that is what it is now.
Because 54 % of the plastic flowed through that function, the saving
propagated across the whole machine at once.

**2. The bracing let the joints get lighter.** Wall went 5.5 -> 4.5 mm
(-22 % on every sleeve annulus) and the sleeves got shorter: post clamps
38 mm, rail collars 26 mm, gusset clamps 28 mm. That is justified by
the diagonals: with shear carried by triangulation, a corner joint no longer
has to be moment-stiff - it only locates the tubes and carries axial load,
and a butted rail takes its compression through the butt face.

**3. The big brackets were solid slabs.** The Y carriage web and X-rod lug
block were ~85 % of that part and both were solid 80 mm-wide blocks; the
Z-rod top arm was a 65 x 138 x 20 slab. All now pocketed.

| Part | was | now | |
|---|---|---|---|
| `Joint4_corner` (x18) | 91 cm3 | **36 cm3** | -61 % |
| `BedCarriage` (x2) | 230 cm3 | **221 cm3** | -4 % |
| `YCarriage` (x2) | 248 cm3 | **164 cm3** | -34 % |
| `ZMotorMount` (x2) | 152 cm3 | **104 cm3** | -31 % |
| `XCarriage` (x1) | 135 cm3 | **202 cm3** | +50 % |
| `CornerTower_R` (x1) | 199 cm3 | **200 cm3** | +1 % |
| `CornerTower_L` (x1) | 192 cm3 | **193 cm3** | +0 % |
| `FootPad` (x4) | 54 cm3 | **38 cm3** | -30 % |
| `Gusset_cap_a` (x2) | 69 cm3 | **49 cm3** | -29 % |
| `Gusset_cap_b` (x2) | 68 cm3 | **48 cm3** | -29 % |
| `TeeZCross` (x4) | 54 cm3 | **23 cm3** | -57 % |
| `YRodBlock` (x4) | 41 cm3 | **22 cm3** | -46 % |
| `Gusset_side_high` (x2) | 69 cm3 | **43 cm3** | -37 % |
| `Gusset_side_low` (x2) | 69 cm3 | **43 cm3** | -37 % |
| `Gusset_rear_low` (x1) | 68 cm3 | **48 cm3** | -30 % |
| `Gusset_rear_high` (x1) | 68 cm3 | **48 cm3** | -30 % |
| **whole machine** | **5481 cm3** | **3266 cm3** | **-40 %** |

Still on the table: **let the tubes CROSS instead of butting into collars**,
which is what Maker Pipe actually does. It removes the collars entirely and
means rails no longer need cutting to length - you clamp anywhere, and you
stop having to thread clamps on from a post end during assembly. The cost
is that every rail shifts one tube diameter off the post centreline, moving
every coordinate in the machine, so the whole clearance set needs
re-verifying. The material saving is real but modest, maybe 20-35 % on the
corners: a crossing clamp is still two sleeves.

The free lever is print settings - these are structural blocks, not
cosmetic. A 0.6 nozzle at 0.3 mm roughly halves the time again.

## Linear motion and hardware

| Qty | Item |
|---|---|
| 2 | 500 mm hardened rod, 12 mm dia - Y axis |
| 1 | MGN12H linear rail, 470 mm - X axis |
| 1 | 2020 extrusion, 470 mm - X beam (the rail needs a straight backing) |
| 4 | 480 mm hardened rod, 10 mm dia - Z |
| 2 | T8 lead screw, 500 mm, 8 mm lead (2 mm x 4 start) + anti-backlash nut |
| 4 | LM12UU (2 per Y carriage; the X axis is a rail now) |
| 4 | LM10UU (bed carriages) |
| 2 | 5 x 8 mm rigid coupler |
| 2 | GT2 20T pulley, 5 mm bore - A and B |
| 6 | GT2 20T toothed idler on M5 stud (2 rear corners, 4 on the Y carriages) |
| ~3 m | GT2 6 mm belt |
| 4 | 2 A NEMA 17 (A, B, Z x2) + 1 smaller for the extruder |
| 1 | 310 x 310 x 3 mm CR-10 heatbed, 24 V 220 W (holes on a 240 mm square) |
| 1 | magnetic sheet + spring steel PEI, 2 mm - the probe needs a FERROUS surface |
| 1 | BTS7960 module, bed switching |
| 1 | 24 V 30 A PSU |
| 1 | thermal cutoff for the bed |

Fasteners are M4 for every conduit pinch bolt, M3 for motors and the
toolhead, M5 for idler studs. I could not confirm any of the rod, bearing,
pulley or belt stock from `~/workshop-inventory` - those boxes are not
photographed yet, so treat this list as *to check*, not *to buy*.

## Wiring the SKR Pico

| Port | Goes to | rotation_distance | steps/mm @16x |
|---|---|---|---|
| X | A motor (rear-left) | 40 | 80 |
| Y | B motor (rear-right) | 40 | 80 |
| Z | both lead screws | 8 | 400 |
| E | extruder | per extruder | - |

**Wire the two Z motors in SERIES into one Z connector**, rather than using
both Z1 and Z2. The board parallels those connectors, and parallel wiring
halves the current to each motor. Series keeps full current in both; it
raises inductance and so caps top speed, which costs nothing on a Z axis
that moves at a few mm/s.

The TMC2209s are good for about 1.4 A RMS with airflow. Run X/Y near
1.0-1.2 A and **fit a fan on the driver heatsink** - BTT's own note is that
anything over 0.8 A wants active cooling.

## The bed, and its power

Sized to a real part: a **POLISI / CR-10 310 x 310 x 3 mm aluminium
heatbed, 24 V 220 W**, about 42 USD, holes on a 240 mm square. Three
things follow from the actual spec rather than a rule of thumb.

**1. It needs 9.17 A, not the 12-20 A a power-density estimate suggests.**
220 W at 24 V is 9.17 A, which is 92 % of the SKR Pico's 10 A hotbed
rating - nominally inside spec, unlike the 288-480 W I first assumed. But
92 % of a rating on a board built for a 120 mm bed is not margin, so put
the BTS7960 in anyway: it is 4 USD, it is 43 A, and the HB output then only
carries the gate signal. **The PSU still needs ~30 A at 24 V** for bed plus
hotend plus four steppers and fans - a reviewer of this exact bed burned a
24 V 15 A supply doing otherwise. Fit a thermal cutoff bonded to the plate
and cap `max_power` in Klipper regardless; a BTS7960 fails shorted.

**2. 220 W over 961 cm2 is only 0.23 W/cm2**, against 0.3-0.5 for a
typical bed. Expect slow heat-up - fine for PLA and PETG, weak for ABS or
ASA, especially unenclosed. **Insulate the underside** (cotton or cork);
it is a few dollars and it matters more here than on a denser bed.

**3. It is 3 mm, and these plates warp.** Reviews of this part report
bowing, one measured at 0.7 mm. It is carried at only four points with a
35 mm overhang all round, so plan on the probe and `bed_mesh` doing real
work - which is the main reason the TL-W5MC1 is in the design at all.

### Mounting it: do not drill the plate

The bed's holes are on a 240 mm square, at (+-120, +-120). The carriages
are at X=+-196 with pads only +-70 in Y, so the patterns do not meet, and
**drilling the plate is not an option** - the heater element is bonded to
its underside and a new hole can cut a trace.

So `BedMount` x4 brings the mount to the bed. Its section is an L: the
flange tucks UNDER the carriage pad and bolts up into it, and the riser
steps up outboard of the pad (Y > 70, where there is no pad) to reach the
plate plane. Nothing shares space with the pad and the bed still lands on
one flat plane. The two bolts sit at X=158 because the carriage spine runs
under X 169..201 - the only strip of pad a flange can tuck beneath is
X 150..169.

## Bed probe - Omron TL-W5MC1

**There is no probe mount in this model, and that is deliberate.** The
earlier side-mounted bracket cost about 49 mm of X travel, because the probe
body has to sit beside the hotend and the nozzle then cannot reach the far
edge of the bed. Two ways to put it back, neither modelled yet:

- a bracket on the **Stealthburner** itself (there are community mounts for
  exactly this sensor), which keeps the frame untouched; or
- skip it and use a **nozzle-contact** probe, which costs no travel at all
  and needs no 24 V level-shifting.

If you do fit the Omron, two things about the sensor matter more than the
mount:

1. **It is 10-30 VDC with an NPN-NO output; the Pico's endstop inputs are
   3.3 V.** Power it from 24 V and the output must not reach the pin
   directly. The output is open-collector, so a pull-up to 3.3 V is the
   clean answer - but **meter the output against ground before connecting
   it**: if it idles at 24 V rather than floating, use a divider or an
   optocoupler instead. Getting this wrong kills the RP2040.
2. **It is inductive, so it only sees ferrous metal.** It will trigger
   reliably on a spring-steel PEI sheet and poorly on bare aluminium. If you
   run a bare aluminium or glass bed, this probe will not work - that is why
   the bed stack above specifies spring steel.

Because Z1/Z2 share a driver, the probe drives `bed_mesh` only. Level the two
screws by hand (turn the couplers independently with the motors unpowered).

## Nozzle wipe and purge dump

`WipeBracket` clamps a dedicated EMT cross rail on the front posts at
z = 460 and reaches back over the frame to hold a brass brush strip just
under the nozzle. One printed part, one extra stick-length of conduit, two
more `Joint4_corner`.

**Where it had to go, and why there was only one choice.** The nozzle can
only be cleaned somewhere it can reach that is not over the bed, and three
constraints close that down to a 10 mm window:

- The **rear is out.** The gantry stops 7.8 mm past the print area there
  before the Y carriages hit the A/B motors - not enough to get a brush in.
- At the **front** there is 32 mm of overtravel, but the Stealthburner
  hangs **39.6 mm ahead of the nozzle**, and the front frame members cross
  the centre at y = -266.0, so the nozzle cannot go below y = -226.4.
- The brush must clear the **bed's sweep**, whose front edge is at
  y = -207.1.

That leaves y = -226.4 .. -216.1. The station sits at y = -221.

**The height is set from above, not below.** This machine moves the *bed* in
Z - the gantry never lifts - so the nozzle is permanently at z = 508.09 and
anything on the frame taller than that is something the toolhead will drive
into. The whole bracket is therefore capped at z = 501 (7.1 mm of
clearance), the brush base sits at z = 497, and a stock ~12 mm brass
bristle stands about 4 mm into the nozzle's path so it wipes under
light compression. Trim or shim the strip; nothing else moves.

**No purge chute.** The column straight down from x = -150 is clear of the
bed, the bottom Z cross rails and all four `BedMount` brackets all the way
to the table, so purged filament just falls. Stand a tin in the front-left
of the frame, roughly 100 x 45 mm centred under the purge point.

Purge sits **50 mm to the left of the brush** so a single +X move wipes
immediately after purging, and so the blob never lands on the bracket
itself - which is what would happen if they shared an X.

### Klipper

Klipper's origin is the front-left corner of the **print area**, and the bed
sits forward by 52.1 mm, so the station is at negative Y in machine
coordinates. Y therefore needs its soft limit opened up:

```ini
[stepper_y]
position_min: -20          # the wipe station lives at Y-18.9
```

```ini
[gcode_macro CLEAN_NOZZLE]
gcode:
    {% if printer.toolhead.homed_axes != "xyz" %}
      G28
    {% endif %}
    G90
    G1 Z20 F1200                  # bed down, out of the way
    G1 X0 Y-18.9 F9000            # purge point
    M109 S240
    G92 E0
    G1 E25 F180                   # dump into the bin
    G92 E0
    G1 E-2 F1800
    G4 P3000                      # let it finish drooling
    {% for i in range(6) %}
      G1 X71 F6000               # drag across the brush
      G1 X29 F6000
    {% endfor %}
    G1 Y11.1 F9000
```

Call it from `PRINT_START` after heating and before the purge line, and from
`PRINT_END`. Six passes is a starting point - the bristles only need to
knock the bead off, and more passes just wear the strip.

## Assembly order

1. Slide all `Joint4_corner` clamps onto the four posts before
   anything else - they are one-piece pinch clamps and only go on from a post
   end. Same for `CornerTower_L/R` and `YRodBlock` on the two rear posts.
2. Build the bottom rectangle and the two Z-motor cross rails, stand the
   posts in it, then the mid, gantry and cap rectangles. Square it before
   final tightening.
3. Z: `ZMotorMount` on the cross rails, motors under, screws and rods up
   through. The rods CANTILEVER - there is no top support - so check the
   bed carriages slide the full 400 mm and the rods stay parallel before
   fitting the bed.
4. Gantry: Y rods into the `YRodBlock`s, Y carriages on, then the 2020 X
   beam with its MGN12 rail clamped between them, the block and
   `XCarriage` on the rail, then the rear corner towers, motors and idlers.
5. Belt the machine. Both beam runs pass through the X carriage at Y=25;
   belt A is the upper plane, belt B the lower.
6. Toolhead, probe, then wiring.

## Verification

`collide.py` samples the machine over a 7 x 7 grid of gantry positions and 5
bed heights and tests every component pair for real 3D overlap; `interfere.py`
runs OpenCASCADE booleans on the built solids and separately asserts that
every post-clamping part actually sits on its post. Current state: **params
PASS, 0 collision violations, 0 solid interferences, all 30 post clamps on
their posts.** Tightest real clearances:

| Pair | mm |
|---|---|
| toolhead / zscrew_m | +1.1 |
| y_carriage_m / zscrew_m | +2.0 |
| y_carriage_p / zscrew_p | +2.0 |
| bed / wipe_bracket | +2.9 |
| bed / x_carriage | +2.9 |
| toolhead / zrod_mm | +3.1 |
| toolhead / zrod_mp | +3.1 |
| toolhead / zrod_pm | +5.5 |
| toolhead / zrod_pp | +5.5 |
| toolhead / zscrew_p | +6.5 |

## What this actually costs

Cheaper than a frame-first look suggests, because the parts that dominate
are all commodity:

| Item | Rough | Note |
|---|---|---|
| 5x 2 A NEMA 17 | ~50 USD | StepperOnline 5-pack |
| 12 mm rod, 500 mm | ~20 USD / pair | Y and X; Z is 10 mm and cheaper |
| Bed, 310 mm | ~42 USD | CR-10 replacement part, 24 V 220 W, 3 mm |
| BTS7960 bed switch | ~4 USD | see the power section |
| EMT frame | ~30 USD | 38 ft of 1/2 in conduit |
| T8 screws, bearings, pulleys, belt | ~80-100 USD | commodity |

**The irreducible cost is not money, it is print time.** 3266 cm3 of solid
part volume across 54 pieces is **1.7-2.1 kg of filament and roughly
90-180 print-hours** (40-50 percent effective density, 15-25 cm3/h). The 16
corner joints alone are ~1450 cm3. A 0.6 nozzle at 0.3 mm roughly halves
that, and these are structural blocks - none of them need a fine layer.

So: the conduit saves perhaps 100-150 USD against 2020 extrusion at this
size, and the whole machine is a few hundred dollars of new parts. What it
costs instead is a few weeks of printer uptime and the bracing compromise.

## Licence and credit

**GPLv3** (see [LICENSE](LICENSE)). The choice is deliberate rather than
reflexive: this machine is designed around the **Voron Stealthburner and
Clockwork 2.5**, which are GPLv3, and a printer meant to be built with
them should carry the same terms.

No Voron geometry is reproduced in this repository. `stage_toolhead()`
draws only a measured *envelope* of the toolhead so the collision checks
have something to test against - the parts you actually print for the
toolhead come from the
[Voron Design repository](https://github.com/VoronDesign/Voron-Trident),
unmodified. Printing somebody else's proven, well-cooled toolhead is
strictly better than remodelling it.

Credit where it is due: the one-piece pinch-clamp joint, which is what
makes a conduit frame work at all, is the form
[Maker Pipe](https://makerpipe.com) popularised for EMT.

## Known soft spots

- **The side planes above the gantry are unbraced**, because the Y
  carriages sweep them - see the bracing section. The rear diagonal and
  the cap plan braces carry that shear; a bolted side panel is the next
  step if it is not enough.
- **An EMT box frame is still not extrusion.** Even triangulated, a pinch
  clamp on round tube can slip under shock load. Tighten the brace
  gussets properly and check them after the first few prints.
- **18 corner joints at 36 cm3 each is the single biggest print** - 640 cm3,
  about a fifth of all the plastic in the machine. If that is too much,
  `CLAMP_WALL` and the socket lengths in `joint4_shape()` are the knobs.
- The lead screws **and the Z rods are unsupported at the top.** The rods
  cantilever 480 mm; the screws carry the weight, so the rods only resist
  pitch and yaw. Standard for this class, but keep Z speed modest.

Two things in here are **not verified against physical parts** and should
be checked before you commit to a whole set of prints:

- **The Stealthburner bolt pattern** (4x M3 at x +-16.3, z -31.61/+19.99)
  is read off the official CAD by measurement, not from a published spec
  sheet. Print **one** `XCarriage` and offer the real toolhead up to it
  before printing anything else that depends on it.
- **There is no bed-probe mount.** The side-mounted bracket that used to be
  here cost about 49 mm of X travel, so it was deleted rather than quietly
  shrinking the build area. See the probe section for the two ways back.

