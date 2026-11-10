# Print list

54 pieces, 26 files. Every file in `stl/` is print-ready as-is: parts that
need the opposite hand have their own `_M` file, so **nothing here depends
on remembering to mirror something in the slicer**.

## Settings

- **PETG or ASA. Not PLA.** Every one of these is a clamp held by bolt
  preload, and PLA creeps under sustained load - the frame would go slack
  over weeks. The bed also radiates onto the lower joints.
- **0.6 mm nozzle, 0.3 mm layers.** These are structural blocks; nothing
  here is cosmetic, and it roughly halves the time against 0.4/0.2.
- **4-5 perimeters, 25-30 % infill.** In a pinch clamp the perimeters
  carry the hoop load, so walls matter far more than infill.
- **No supports needed on any part.** That is measured, not assumed:
  `printability.py` finds each part's outward face normals, picks the
  orientation, and reports downward-facing area steeper than 45 degrees.
  It comes to ZERO for every part - the geometry is all axis-aligned
  boxes and cylinders, so every downward face is either vertical (fine)
  or horizontal (a bridge).
- **Brim on the 11 part types marked below.** Their bed face is as little
  as 314 mm2 - a clamp sleeve end-annulus - which is not much to hold a
  tall part down.
- The longest bridges are 43 mm (`CornerTower_L`), 38 mm (`Gusset_side_high`), 38 mm (`Gusset_side_low`).
  Those will sag slightly on the underside; it is cosmetic, and none of
  them is a mating face.
- Check the slicer is not bridging the 2.2 mm pinch slots closed - they
  have to stay open or the clamp cannot pinch.
- Bores are a clearance fit with a pinch slot (18.38 mm bore on a 17.93 mm
  tube), so a little sag in a horizontally-printed bore is tolerable -
  the bolt pulls it round. Ream it if a tube will not start.

## Batch 1 - Frame

| File | Qty | cm3 | Print it | Bed mm2 | Notes |
|---|---|---|---|---|---|
| `Joint4_corner.stl` | 18 | 36 | as modelled, +Z up | 710 | **brim** |
| `FootPad.stl` | 4 | 38 | as modelled, +Z up | 2463 | - |
| `TeeZCross.stl` | 2 | 23 | upside down (rotate 180 about X) | 651 | **brim** |
| `TeeZCross_M.stl` | 2 | 23 | mirror of the above | 651 | **brim** |

26 pieces, 885 cm3 -> about 0.45-0.56 kg, 14-29 h.

## Batch 2 - Bracing

| File | Qty | cm3 | Print it | Bed mm2 | Notes |
|---|---|---|---|---|---|
| `Gusset_cap_a.stl` | 2 | 49 | upside down (rotate 180 about X) | 355 | **brim**, 37 mm bridge |
| `Gusset_cap_b.stl` | 2 | 48 | upside down (rotate 180 about X) | 355 | **brim**, 37 mm bridge |
| `Gusset_side_high.stl` | 1 | 43 | on its side, -X up (rotate +90 about Y) | 710 | **brim**, 38 mm bridge |
| `Gusset_side_high_M.stl` | 1 | 43 | mirror of the above | 710 | **brim**, 38 mm bridge |
| `Gusset_side_low.stl` | 1 | 43 | on its side, -X up (rotate +90 about Y) | 710 | **brim**, 38 mm bridge |
| `Gusset_side_low_M.stl` | 1 | 43 | mirror of the above | 710 | **brim**, 38 mm bridge |
| `Gusset_rear_low.stl` | 1 | 48 | on its front, -Y up (rotate +90 about X) | 355 | **brim**, 33 mm bridge |
| `Gusset_rear_high.stl` | 1 | 48 | on its front, -Y up (rotate +90 about X) | 355 | **brim**, 33 mm bridge |

10 pieces, 464 cm3 -> about 0.24-0.29 kg, 7-15 h.

## Batch 3 - Z axis

| File | Qty | cm3 | Print it | Bed mm2 | Notes |
|---|---|---|---|---|---|
| `BedCarriage.stl` | 1 | 221 | upside down (rotate 180 about X) | 6507 | - |
| `BedCarriage_M.stl` | 1 | 221 | mirror of the above | 6507 | - |
| `BedMount.stl` | 2 | 52 | as modelled, +Z up | 3333 | - |
| `BedMount_M.stl` | 2 | 52 | mirror of the above | 3333 | - |
| `ZMotorMount.stl` | 1 | 104 | as modelled, +Z up | 3833 | - |
| `ZMotorMount_M.stl` | 1 | 104 | mirror of the above | 3833 | - |

8 pieces, 860 cm3 -> about 0.44-0.55 kg, 14-29 h.

## Batch 4 - Gantry

| File | Qty | cm3 | Print it | Bed mm2 | Notes |
|---|---|---|---|---|---|
| `YCarriage.stl` | 1 | 164 | upside down (rotate 180 about X) | 355 | **brim** |
| `YCarriage_M.stl` | 1 | 164 | mirror of the above | 355 | **brim** |
| `XCarriage.stl` | 1 | 202 | on its side, +X up (rotate -90 about Y) | 3510 | - |
| `CornerTower_R.stl` | 1 | 200 | as modelled, +Z up | 3236 | - |
| `CornerTower_L_M.stl` | 1 | 193 | mirror of the above | 2149 | 43 mm bridge |
| `YRodBlock.stl` | 2 | 22 | as modelled, +Z up | 314 | **brim** |
| `YRodBlock_M.stl` | 2 | 22 | mirror of the above | 314 | **brim** |

9 pieces, 1012 cm3 -> about 0.51-0.64 kg, 16-34 h.

## Batch 5 - Wipe station

| File | Qty | cm3 | Print it | Bed mm2 | Notes |
|---|---|---|---|---|---|
| `WipeBracket.stl` | 1 | 46 | on its front, -Y up (rotate +90 about X) | 576 | **brim** |

1 piece, 46 cm3 -> about 0.02-0.03 kg, 1-2 h.

## Total

**54 pieces, 3266 cm3** = 1.7-2.1 kg and roughly 52-109 print-hours
at 40-50 % effective density and 15-25 cm3/h.

Batches are in assembly order, so you can start building the frame while
the rest prints. Batch 1 alone (26 pieces) gets the whole frame standing.

## Print the frame joints first and check one

`Joint4_corner` is 18 of the 54 pieces. Print **one**, put it on a real
piece of conduit and tighten the bolt before committing to the other 17:
the bore is sized from the nominal 17.93 mm OD and real EMT wanders about
+-0.1 mm between makes. If it is tight, raise `EMT_FIT` in `params.py`
(currently 0.45 mm) and re-run; if it is sloppy, lower it.
