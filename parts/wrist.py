"""Compact wrist stack — short pitch/roll/yaw."""

from __future__ import annotations

import math

import Part

import params as P
from cad.sketch_pad import cut, cyl, fuse, pad_xy, rotate, translate
from parts.joint_features import bearing_seat, horn_screws, horn_well, insert_m3, servo_body_pocket, shaft_clearance, tab_holes


def make_wrist_pitch_yoke() -> Part.Shape:
    p = P.MG90S
    plate = pad_xy([(-10, -10), (10, -10), (10, 10), (-10, 10)], 4.5)
    cheek_t, arm_l = 3.5, 32.0
    gap = p["body_w"] + 4
    cheek_h = p["body_h_total"] + 5
    left = pad_xy([(6, -gap / 2 - cheek_t), (6 + arm_l, -gap / 2 - cheek_t), (6 + arm_l, -gap / 2), (6, -gap / 2)], cheek_h, z0=4.5 - cheek_h / 2)
    right = pad_xy([(6, gap / 2), (6 + arm_l, gap / 2), (6 + arm_l, gap / 2 + cheek_t), (6, gap / 2 + cheek_t)], cheek_h, z0=4.5 - cheek_h / 2)
    bridge = pad_xy([(6 + arm_l - 6, -gap / 2 - cheek_t), (6 + arm_l, -gap / 2 - cheek_t), (6 + arm_l, gap / 2 + cheek_t), (6 + arm_l - 6, gap / 2 + cheek_t)], 4, z0=2)
    body = fuse([plate, left, right, bridge])
    cx = 6 + arm_l / 2
    cuts = [horn_well(p, 2.3), cyl(2.5, 8, (0, 0, -3)), horn_screws(p, 11, 4, -3)]
    cuts.append(translate(servo_body_pocket(p), cx, 0, 2))
    cuts.append(tab_holes(p, cheek_h / 2 + 1))
    cuts.append(translate(rotate(bearing_seat(P.F685ZZ, "+z"), (1, 0, 0), 90), cx, -gap / 2 - cheek_t / 2, 2))
    cuts.append(translate(rotate(bearing_seat(P.F685ZZ, "+z"), (1, 0, 0), -90), cx, gap / 2 + cheek_t / 2, 2))
    cuts.append(shaft_clearance(gap + 2 * cheek_t + 4, (cx, -gap / 2 - cheek_t - 2, 2), "y"))
    return cut(body, cuts)


def make_wrist_roll_carrier() -> Part.Shape:
    p = P.MG90S
    plate = pad_xy([(-9, -9), (9, -9), (9, 9), (-9, 9)], 4.5)
    tube_od, tube_l = 28.0, 30.0
    tube = cyl(tube_od / 2, tube_l, (6, 0, 2.2), "x")
    body = fuse([plate, tube])
    hollow = cyl(tube_od / 2 - P.WALL, tube_l - 3, (8, 0, 2.2), "x")
    pocket = translate(rotate(servo_body_pocket(p), (0, 1, 0), 90), 6 + tube_l / 2, 0, 2.2)
    bp = translate(rotate(bearing_seat(P.F685ZZ, "+z"), (0, 1, 0), 90), 6 + tube_l - 1.5, 0, 2.2)
    shaft = shaft_clearance(14, (6 + tube_l - 8, 0, 2.2), "x")
    cuts = [horn_well(p, 2.3), cyl(2.5, 8, (0, 0, -3)), horn_screws(p, 11, 4, -3), hollow, pocket, bp, shaft]
    for ang in (0, 180):
        cuts.append(insert_m3((14, 6 * math.cos(math.radians(ang)), 2.2 + 6 * math.sin(math.radians(ang))), "x"))
    return cut(body, cuts)


def make_wrist_yaw_flange() -> Part.Shape:
    p = P.MG90S
    plate = pad_xy([(-12, -12), (12, -12), (12, 12), (-12, 12)], 4.5)
    cuts = [horn_well(p, 2.3), cyl(2.5, 8, (0, 0, -3)), horn_screws(p, 11, 4, -3)]
    for x in (-8, 8):
        for y in (-8, 8):
            cuts.append(insert_m3((x, y, 4.3)))
    return cut(plate, cuts)


def make_all():
    return {
        "12_wrist_pitch_yoke": make_wrist_pitch_yoke(),
        "13_wrist_roll_carrier": make_wrist_roll_carrier(),
        "14_wrist_yaw_flange": make_wrist_yaw_flange(),
    }
