"""Compact camera mount."""

from __future__ import annotations

import Part

import params as P
from cad.sketch_pad import cut, cyl, fuse, pad_xy, translate
from parts.joint_features import horn_screws, horn_well, insert_m3, servo_body_pocket, tab_holes


def make_camera_bracket() -> Part.Shape:
    p = P.MG90S
    bl = P.CAM_BOARD_L + 2 * P.CAM_SLOT_CLEAR
    bw = P.CAM_BOARD_W + 2 * P.CAM_SLOT_CLEAR
    plate = pad_xy([(-(bl + 6) / 2, -9), ((bl + 6) / 2, -9), ((bl + 6) / 2, 9), (-(bl + 6) / 2, 9)], 5)
    slot = pad_xy([(-bl / 2, -bw / 2), (bl / 2, -bw / 2), (bl / 2, bw / 2), (-bl / 2, bw / 2)], 1.8, z0=3.2)
    lens = cyl(P.CAM_LENS_D / 2 + 0.35, 8, (18, 0, -1.5))
    horn = pad_xy([(-10, -10), (10, -10), (10, 10), (-10, 10)], 4.5, z0=-4.5)
    body = fuse([plate, horn])
    cuts = [slot, lens, horn_well(p, 2.3), cyl(2.5, 10, (0, 0, -7)), horn_screws(p, 11, 4, -7)]
    return cut(body, cuts)


def make_camera_tilt_mount() -> Part.Shape:
    p = P.MG90S
    L, W, H = p["tab_l"] + 8, p["body_w"] + 2 * P.WALL + 5, p["body_h_total"] + 4
    shell = pad_xy([(-L / 2, -W / 2), (L / 2, -W / 2), (L / 2, W / 2), (-L / 2, W / 2)], H)
    pocket = translate(servo_body_pocket(p), 0, 0, H / 2)
    mounts = []
    for x in (-10, 10):
        for y in (-6, 6):
            mounts.append(cyl(P.M3["clear_d"] / 2, H + 2, (x, y, -1)))
            mounts.append(insert_m3((x, y, H - 0.2)))
    return cut(shell, [pocket, tab_holes(p, H - 1)] + mounts)


def make_all():
    return {"19_camera_bracket": make_camera_bracket(), "20_camera_tilt_mount": make_camera_tilt_mount()}
