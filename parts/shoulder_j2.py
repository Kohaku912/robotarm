"""J2 horn clamp + idler press boss — bolts to upper arm plates."""

from __future__ import annotations

import Part

import params as P
from cad.sketch_pad import cut, cyl, fuse, pad_xy
from parts.joint_features import horn_screws, horn_well, insert_m3, shaft_press_boss


def make_shoulder_horn_clamp() -> Part.Shape:
    p = P.MG996R
    plate = pad_xy([(-15, -15), (15, -15), (15, 15), (-15, 15)], 5)
    flange = pad_xy([(6, -12), (34, -12), (34, 12), (6, 12)], 7)
    body = fuse([plate, flange])
    cuts = [horn_well(p, 2.6), cyl(3.2, 10, (0, 0, -4)), horn_screws(p, 15.0, 4, -4)]
    for y in (-7, 7):
        for z in (2, 5):
            cuts.append(insert_m3((36, y, z), "x"))
    cuts.append(cyl(P.CABLE_HOLE_D / 2, 20, (16, 0, -4), "x"))
    return cut(body, cuts)


def make_shoulder_idler_cap() -> Part.Shape:
    plate = pad_xy([(-14, -11), (14, -11), (14, 11), (-14, 11)], 4.5)
    outer = cyl(9, 3.5, (0, 0, 4.5))
    press = shaft_press_boss(5.0, (0, 0, 4.5))
    body = fuse([plate, outer, press])
    cuts = []
    for y in (-7, 7):
        for x in (-8, 8):
            cuts.append(insert_m3((x, y, 4.3)))
    cuts.append(cyl(P.M3["clear_d"] / 2, 10, (-5, 0, 6.5), "x"))
    return cut(body, cuts)


def make_all():
    return {
        "04_shoulder_horn_clamp": make_shoulder_horn_clamp(),
        "05_shoulder_idler_cap": make_shoulder_idler_cap(),
    }
