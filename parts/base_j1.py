"""Compact J1: low base, vertical MG996R, horn-driven turntable, dual F695."""

from __future__ import annotations

import math

import Part

import params as P
from cad.sketch_pad import cut, cyl, fuse, pad_xy, translate
from parts.joint_features import (
    bearing_seat,
    horn_screws,
    horn_well,
    insert_m3,
    retainer_ring_holes,
    servo_body_pocket,
    soft_stop_pad,
    tab_holes,
)


def make_base_plate() -> Part.Shape:
    plate = cyl(P.BASE_OD / 2, P.BASE_PLATE)
    holes = []
    for i in range(P.BASE_MOUNT_HOLES):
        ang = i * 360.0 / P.BASE_MOUNT_HOLES
        x = (P.BASE_MOUNT_HOLE_PCD / 2) * math.cos(math.radians(ang))
        y = (P.BASE_MOUNT_HOLE_PCD / 2) * math.sin(math.radians(ang))
        holes.append(cyl(P.M4["clear_d"] / 2, P.BASE_PLATE + 2, (x, y, -1)))
        holes.append(cyl(P.M4["head_d"] / 2, P.M4["head_h"] + 0.3, (x, y, -0.1)))
    # center clearance for cables under servo
    holes.append(cyl(10, P.BASE_PLATE + 2, (0, 0, -1)))
    return cut(plate, holes)


def make_base_column() -> Part.Shape:
    """Low well holding MG996R upright; top F695 seat for turntable."""
    p = P.MG996R
    ol = p["tab_l"] + 10
    ow = p["body_w"] + 2 * P.WALL + 8
    oh = P.TURNTABLE_Z - P.BASE_PLATE - 2
    z0 = P.BASE_PLATE
    shell = pad_xy([(-ol / 2, -ow / 2), (ol / 2, -ow / 2), (ol / 2, ow / 2), (-ol / 2, ow / 2)], oh, z0=z0)
    pocket = translate(servo_body_pocket(p), 0, 0, z0 + oh / 2 - 1)
    body = cut(shell, [pocket, tab_holes(p, z0 + oh - 8)])
    # cable exit
    body = cut(body, [pad_xy([(-5, -ow / 2 - 1), (5, -ow / 2 - 1), (5, -ow / 2 + 6), (-5, -ow / 2 + 6)], 5, z0=z0 + 3)])
    boss = cyl(11, 4, (0, 0, z0 + oh - 1))
    body = fuse([body, boss])
    bp = translate(bearing_seat(P.F695ZZ, "+z"), 0, 0, z0 + oh + 1)
    body = cut(body, [bp, cyl(3.4, 14, (0, 0, z0 + oh - 4)), retainer_ring_holes(16, 4, z0 + oh)])
    return body


def make_turret() -> Part.Shape:
    """Compact turntable + short shoulder yoke; MG996R for J2 INSIDE cheeks."""
    p = P.MG996R
    deck_t = 5.0
    deck = pad_xy([(-28, -24), (28, -24), (28, 24), (-28, 24)], deck_t)
    # horn coupler
    cuts = [horn_well(p, 2.8), cyl(3.2, 10, (0, 0, -4)), horn_screws(p, 15.0, 4, -4)]
    # underside J1 bearing
    ring = cyl(12, 4, (0, 0, -4))
    body = fuse([deck, ring])
    cuts.append(translate(bearing_seat(P.F695ZZ, "-z"), 0, 0, -2))
    cuts.append(cyl(3.4, 12, (0, 0, -6)))

    # Short U yoke — plates along XZ, thickness Y, inner span YOKE_INNER
    cheek_t = P.PLATE_T
    cheek_l = 48.0
    cheek_h = P.YOKE_HEIGHT
    y_half = P.YOKE_INNER / 2
    left = pad_xy(
        [(-cheek_l / 2, -y_half - cheek_t), (cheek_l / 2, -y_half - cheek_t), (cheek_l / 2, -y_half), (-cheek_l / 2, -y_half)],
        cheek_h,
        z0=deck_t,
    )
    right = pad_xy(
        [(-cheek_l / 2, y_half), (cheek_l / 2, y_half), (cheek_l / 2, y_half + cheek_t), (-cheek_l / 2, y_half + cheek_t)],
        cheek_h,
        z0=deck_t,
    )
    # spacers (printed bosses)
    sp1 = pad_xy([(-8, -y_half), (8, -y_half), (8, y_half), (-8, y_half)], 4, z0=deck_t + 8)
    sp2 = pad_xy([(-8, -y_half), (8, -y_half), (8, y_half), (-8, y_half)], 4, z0=deck_t + cheek_h - 12)
    body = fuse([body, left, right, sp1, sp2])

    piv_x = 6.0
    piv_z = deck_t + 28.0  # low shoulder pivot
    from cad.sketch_pad import rotate

    bp_l = translate(rotate(bearing_seat(P.F695ZZ, "+z"), (1, 0, 0), 90), piv_x, -y_half - cheek_t / 2, piv_z)
    bp_r = translate(rotate(bearing_seat(P.F695ZZ, "+z"), (1, 0, 0), -90), piv_x, y_half + cheek_t / 2, piv_z)
    from parts.joint_features import shaft_clearance

    shaft = shaft_clearance(P.YOKE_INNER + 2 * cheek_t + 6, (piv_x, -y_half - cheek_t - 3, piv_z), "y")
    # internal servo clear (body between cheeks)
    servo_clear = pad_xy(
        [
            (-p["body_l"] / 2 + piv_x, -y_half),
            (p["body_l"] / 2 + piv_x, -y_half),
            (p["body_l"] / 2 + piv_x, y_half),
            (-p["body_l"] / 2 + piv_x, y_half),
        ],
        p["body_h_total"] + 2,
        z0=piv_z - p["body_h_total"] / 2 - 1,
    )
    inserts = []
    for y in (-y_half - cheek_t / 2, y_half + cheek_t / 2):
        for dx, dz in ((-10, 10), (10, 10), (-10, -10), (10, -10)):
            inserts.append(insert_m3((piv_x + dx, y - 2.5, piv_z + dz), "y"))

    stop_a = translate(soft_stop_pad(5, 3), piv_x + 18, -8, deck_t)
    stop_b = translate(soft_stop_pad(5, 3), piv_x + 18, 8, deck_t)
    body = fuse([body, stop_a, stop_b])
    body = cut(body, cuts + [bp_l, bp_r, shaft, servo_clear] + inserts)
    return body


def make_all():
    return {
        "01_base_plate": make_base_plate(),
        "02_base_column": make_base_column(),
        "03_turret": make_turret(),
    }
