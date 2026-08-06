"""Compact elbow horn + idler."""

from __future__ import annotations

import Part

import params as P
from cad.sketch_pad import cut, cyl, fuse, pad_xy
from parts.joint_features import horn_screws, horn_well, insert_m3, shaft_press_boss


def make_elbow_horn_clamp() -> Part.Shape:
    p = P.MG90S
    plate = pad_xy([(-11, -11), (11, -11), (11, 11), (-11, 11)], 4.5)
    flange = pad_xy([(5, -9), (28, -9), (28, 9), (5, 9)], 6)
    body = fuse([plate, flange])
    cuts = [horn_well(p, 2.4), cyl(2.5, 10, (0, 0, -4)), horn_screws(p, 12.0, 4, -4)]
    for y in (-6, 6):
        for z in (1.8, 4.2):
            cuts.append(insert_m3((30, y, z), "x"))
    return cut(body, cuts)


def make_elbow_idler() -> Part.Shape:
    plate = pad_xy([(-10, -9), (10, -9), (10, 9), (-10, 9)], 4)
    outer = cyl(7.5, 3, (0, 0, 4))
    press = shaft_press_boss(4.5, (0, 0, 4))
    body = fuse([plate, outer, press])
    cuts = [insert_m3((x, y, 3.8)) for x in (-6, 6) for y in (-5, 5)]
    cuts.append(cyl(P.M3["clear_d"] / 2, 8, (-4, 0, 5.5), "x"))
    return cut(body, cuts)


def make_all():
    return {"08_elbow_horn_clamp": make_elbow_horn_clamp(), "09_elbow_idler": make_elbow_idler()}
