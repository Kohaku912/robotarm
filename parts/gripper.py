"""Compact gripper."""

from __future__ import annotations

import FreeCAD as App
import Part

import params as P
from cad.sketch_pad import cut, cyl, fuse, pad_xy, translate
from parts.joint_features import servo_body_pocket, tab_holes


def make_gripper_body() -> Part.Shape:
    p = P.MG90S
    L, W, H = P.GRIPPER_BODY_L, P.GRIPPER_BODY_W, P.GRIPPER_BODY_H
    body = pad_xy([(-L / 2, -W / 2), (L / 2, -W / 2), (L / 2, W / 2), (-L / 2, W / 2)], H)
    pocket = translate(servo_body_pocket(p), -5, 0, H / 2)
    rails = [
        pad_xy([(-L / 2 + 3, -W / 2 + 2.5), (L / 2 - 3, -W / 2 + 2.5), (L / 2 - 3, -W / 2 + 5.2), (-L / 2 + 3, -W / 2 + 5.2)], 3.5, z0=H / 2 - 1.5),
        pad_xy([(-L / 2 + 3, W / 2 - 5.2), (L / 2 - 3, W / 2 - 5.2), (L / 2 - 3, W / 2 - 2.5), (-L / 2 + 3, W / 2 - 2.5)], 3.5, z0=H / 2 - 1.5),
    ]
    mounts = []
    for x in (-8, 8):
        for y in (-8, 8):
            mounts.append(cyl(P.M3["clear_d"] / 2, H + 2, (x, y, -1)))
            mounts.append(cyl(P.M3["head_d"] / 2, P.M3["head_h"] + 0.3, (x, y, -0.1)))
    window = pad_xy([(-14, -7), (2, -7), (2, 7), (-14, 7)], H + 2, z0=-1)
    return cut(body, [pocket, tab_holes(p, H - 1)] + rails + mounts + [window])


def _finger() -> Part.Shape:
    L, T, W = P.FINGER_LEN, P.FINGER_THICK, P.FINGER_WIDTH
    finger = pad_xy([(0, -W / 2), (L, -W / 2), (L, W / 2), (0, W / 2)], T)
    pad = pad_xy([(L - 8, -(W + 1) / 2), (L, -(W + 1) / 2), (L, (W + 1) / 2), (L - 8, (W + 1) / 2)], T + 0.8, z0=-0.4)
    tenon = pad_xy([(3, -1.2), (L - 4, -1.2), (L - 4, 1.2), (3, 1.2)], 3, z0=T)
    body = fuse([finger, pad, tenon])
    return cut(body, [cyl(1.5, W + 3, (10, -W / 2 - 1.5, T / 2), "y")])


def make_finger_left() -> Part.Shape:
    return _finger()


def make_finger_right() -> Part.Shape:
    return _finger().mirror(App.Vector(0, 0, 0), App.Vector(0, 1, 0))


def make_linkage() -> Part.Shape:
    bar = pad_xy([(-12, -2.5), (12, -2.5), (12, 2.5), (-12, 2.5)], 2.5)
    return cut(bar, [cyl(1.5, 5, (-8, 0, -1)), cyl(1.5, 5, (8, 0, -1))])


def make_all():
    return {
        "15_gripper_body": make_gripper_body(),
        "16_finger_left": make_finger_left(),
        "17_finger_right": make_finger_right(),
        "18_gripper_link": make_linkage(),
    }
