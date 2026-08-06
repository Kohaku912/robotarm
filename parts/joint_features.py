"""Shared features for compact internal-servo plate arm."""

from __future__ import annotations

import math

import Part

import params as P
from cad.sketch_pad import cut, cyl, fuse, pad_xy, rotate, translate


def servo_body_pocket(servo: dict, extra: float = None) -> Part.Shape:
    e = P.SERVO_POCKET_EXTRA if extra is None else extra
    bl = servo["body_l"] + 2 * e
    bw = servo["body_w"] + 2 * e
    bh = servo["body_h_total"] + e
    body = pad_xy(
        [(-bl / 2, -bw / 2), (bl / 2, -bw / 2), (bl / 2, bw / 2), (-bl / 2, bw / 2)],
        bh,
        z0=-bh / 2,
    )
    cable = pad_xy(
        [
            (-servo["cable_clear_w"] / 2, -bw / 2 - 5),
            (servo["cable_clear_w"] / 2, -bw / 2 - 5),
            (servo["cable_clear_w"] / 2, -bw / 2),
            (-servo["cable_clear_w"] / 2, -bw / 2),
        ],
        servo["cable_clear_h"],
        z0=-bh / 2,
    )
    return fuse([body, cable])


def tab_holes(servo: dict, z: float) -> Part.Shape:
    along = servo["tab_hole_along"] / 2
    across = servo.get("tab_hole_across", 0) / 2
    d = servo["tab_hole_d"]
    ys = (-across, across) if across > 0.1 else (0.0,)
    holes = []
    for x in (-along, along):
        for y in ys:
            holes.append(cyl(d / 2, 20, (x, y, z - 10)))
    return fuse(holes)


def bearing_seat(spec: dict, flange_out: str = "+z") -> Part.Shape:
    od = spec["seat_od"]
    w = spec["width"] + 0.25
    fod = spec["flange_seat"]
    ft = spec["flange_t"] + 0.2
    seat = cyl(od / 2, w, (0, 0, -w / 2))
    fl = cyl(fod / 2, ft, (0, 0, w / 2 - ft if flange_out == "+z" else -w / 2))
    return fuse([seat, fl])


def horn_well(servo: dict, depth: float = 2.8) -> Part.Shape:
    return cyl(servo["horn_circle_d"] / 2 + 0.35, depth, (0, 0, -0.1))


def horn_screws(servo: dict, pcd: float = None, n: int = 4, z: float = -4) -> Part.Shape:
    pcd = pcd or (servo["horn_circle_d"] * 0.75)
    r = pcd / 2
    holes = []
    for i in range(n):
        ang = i * 360.0 / n
        holes.append(cyl(1.15, 12, (r * math.cos(math.radians(ang)), r * math.sin(math.radians(ang)), z)))
    return fuse(holes)


def insert_m3(origin, axis="z") -> Part.Shape:
    return cyl(P.M3["insert_hole"] / 2, P.M3["insert_depth"], origin, axis)


def shaft_clearance(length: float, origin, axis: str = "z") -> Part.Shape:
    return cyl(P.SHAFT_CLEAR / 2, length, origin, axis)


def shaft_press_boss(height: float, origin=(0, 0, 0), axis: str = "z") -> Part.Shape:
    return cyl(P.SHAFT_FIT / 2, height, origin, axis)


def soft_stop_pad(size: float = 5.0, thick: float = 3.5) -> Part.Shape:
    return pad_xy([(-size / 2, -size / 2), (size / 2, -size / 2), (size / 2, size / 2), (-size / 2, size / 2)], thick)


def side_plate(length: float, height: float, thick: float = None) -> Part.Shape:
    """XY footprint extruded in Z — plate in XZ, thickness along Y when rotated later."""
    t = P.PLATE_T if thick is None else thick
    return pad_xy([(0, 0), (length, 0), (length, height), (0, height)], t)


def retainer_ring_holes(pcd: float = 18.0, n: int = 4, z: float = 0) -> Part.Shape:
    holes = []
    for i in range(n):
        ang = i * 360.0 / n
        holes.append(cyl(P.M3["clear_d"] / 2, 12, (pcd / 2 * math.cos(math.radians(ang)), pcd / 2 * math.sin(math.radians(ang)), z - 6)))
    return fuse(holes)


# Re-export fastener spec
from parts.fastener_spec import FASTENER_REQUIREMENTS  # noqa: E402
