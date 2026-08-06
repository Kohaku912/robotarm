# Realistic redesign notes — sources and mechanical rationale

## Reference projects

| Project | Reach | Payload | Actuators | Takeaway |
|---------|-------|---------|-----------|----------|
| OmArm Zero | ~303 mm | ~141 g | 3× MG996R + 3× SG90 | With only 2× MG996R, keep reach ~350 mm and short distal links |
| Omartronics 6-DOF | hobby | light | MG996R base/shoulder/elbow | Base servo + bearing under turret; U-yoke shoulder |
| Typical servo arm | — | — | horn + opposite bearing | Load path never through servo case alone |
| Thor | 625 mm | 750 g | steppers + belts | Structural inspiration only; not used (wrong actuators) |

## Joint pattern (applied to every revolute joint)

1. Servo body pocket with datasheet tab-hole spacing
2. Circular horn bolted to the driven link
3. Opposite cheek: flanged bearing seat + Ø5 shaft through bearing ID
4. Cable pass-through with rounded entry
5. Soft mechanical stops near ±90° (servo 180° class)

## Bearing allocation (stock exact)

- F695ZZ ×5: J1×2, J2×2, J3×1
- F685ZZ ×5: J4×2, J5×2, J6×1

## Link lengths (axis to axis)

- Upper arm: 140 mm (split 70+70 for 180 mm bed)
- Forearm: 120 mm (split 60+60)
- Wrist stack: ~70 mm
- Approx reach (J1 axis to wrist flange): ~350 mm

## Hardware dimensions (rebuilt from published specs, not copied CAD)

- MG996R: body ~40.7×19.7, tab length ~54.5, hole pitch ~49.5×10
- MG90S: body ~22.8×12.2×28.5, tab hole pitch ~28
- F695ZZ: 5×13×4, flange Ø15
- F685ZZ: 5×11×5, flange Ø12.5

## CAD method

1. Draw 2D profiles (`docs/2d/*.svg` + sketch point loops)
2. Extrude / pocket via `cad/sketch_pad.py` (Sketch→Pad equivalent)
3. Fit-check against `vendor/` solids
4. Export STL + URDF; drive with PyBullet position-controlled joints

## Torque note

MG996R ~10 kg·cm. Tip 100 g at 350 mm ≈ 3.5 kg·cm from payload alone; self-weight adds more.
Shoulder (J2) is the bottleneck. Elbow on MG90S requires the shorter forearm.
