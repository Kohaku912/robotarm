"""Vendor reference solids from published dimensions (not copied proprietary CAD)."""

from __future__ import annotations

import math
import os

import FreeCAD as App
import Part

import params as P
from cad.sketch_pad import V, cut, cyl, fuse, pad_xy, translate


def mg996r() -> Part.Shape:
    p = P.MG996R
    # body extruded from XY rectangle
    body = pad_xy(
        [
            (-p["body_l"] / 2, -p["body_w"] / 2),
            (p["body_l"] / 2, -p["body_w"] / 2),
            (p["body_l"] / 2, p["body_w"] / 2),
            (-p["body_l"] / 2, p["body_w"] / 2),
        ],
        p["body_h_total"],
        z0=0,
    )
    tab = pad_xy(
        [
            (-p["tab_l"] / 2, -p["tab_w"] / 2),
            (p["tab_l"] / 2, -p["tab_w"] / 2),
            (p["tab_l"] / 2, p["tab_w"] / 2),
            (-p["tab_l"] / 2, p["tab_w"] / 2),
        ],
        p["tab_t"],
        z0=p["tab_z_from_bottom"],
    )
    along = p["tab_hole_along"] / 2
    across = p["tab_hole_across"] / 2
    holes = []
    for x in (-along, along):
        for y in (-across, across) if across > 0 else (0,):
            holes.append(cyl(p["tab_hole_d"] / 2, 20, (x, y, p["tab_z_from_bottom"] - 5)))
    shaft = cyl(p["spline_d"] / 2, p["spline_h"], (0, 0, p["body_h_total"]))
    return cut(fuse([body, tab, shaft]), holes)


def mg90s() -> Part.Shape:
    p = P.MG90S
    body = pad_xy(
        [
            (-p["body_l"] / 2, -p["body_w"] / 2),
            (p["body_l"] / 2, -p["body_w"] / 2),
            (p["body_l"] / 2, p["body_w"] / 2),
            (-p["body_l"] / 2, p["body_w"] / 2),
        ],
        p["body_h_total"],
    )
    tab = pad_xy(
        [
            (-p["tab_l"] / 2, -p["tab_w"] / 2),
            (p["tab_l"] / 2, -p["tab_w"] / 2),
            (p["tab_l"] / 2, p["tab_w"] / 2),
            (-p["tab_l"] / 2, p["tab_w"] / 2),
        ],
        p["tab_t"],
        z0=p["tab_z_from_bottom"],
    )
    along = p["tab_hole_along"] / 2
    holes = [cyl(p["tab_hole_d"] / 2, 16, (x, 0, p["tab_z_from_bottom"] - 4)) for x in (-along, along)]
    shaft = cyl(p["spline_d"] / 2, p["spline_h"], (0, 0, p["body_h_total"]))
    return cut(fuse([body, tab, shaft]), holes)


def bearing(spec: dict) -> Part.Shape:
    outer = cyl(spec["od"] / 2, spec["width"], (0, 0, 0))
    flange = cyl(spec["flange_od"] / 2, spec["flange_t"], (0, 0, spec["width"] - spec["flange_t"]))
    bore = cyl(spec["id"] / 2, spec["width"] + 2, (0, 0, -1))
    return cut(fuse([outer, flange]), [bore])


def f695zz() -> Part.Shape:
    return bearing(P.F695ZZ)


def f685zz() -> Part.Shape:
    return bearing(P.F685ZZ)


def circular_horn(outer_d: float, hub_d: float, thick: float, screw_pcd: float, screw_d: float, n: int = 4) -> Part.Shape:
    disc = cyl(outer_d / 2, thick)
    hub = cyl(hub_d / 2 + 1.5, thick + 1.5, (0, 0, 0))
    body = fuse([disc, hub])
    bore = cyl(hub_d / 2, thick + 4, (0, 0, -1))
    screws = []
    for i in range(n):
        ang = i * 360.0 / n
        x = (screw_pcd / 2) * math.cos(math.radians(ang))
        y = (screw_pcd / 2) * math.sin(math.radians(ang))
        screws.append(cyl(screw_d / 2, thick + 4, (x, y, -1)))
    return cut(body, [bore] + screws)


def horn_mg996r() -> Part.Shape:
    return circular_horn(20.0, 5.9, 2.0, 15.0, 2.2, 4)


def horn_mg90s() -> Part.Shape:
    return circular_horn(16.0, 4.8, 1.8, 12.0, 1.8, 4)


def export_step(shape: Part.Shape, path: str):
    shape.exportStep(path)


def export_all(out_dir: str):
    os.makedirs(out_dir, exist_ok=True)
    items = {
        "MG996R": mg996r(),
        "MG90S": mg90s(),
        "F695ZZ": f695zz(),
        "F685ZZ": f685zz(),
        "horn_MG996R": horn_mg996r(),
        "horn_MG90S": horn_mg90s(),
    }
    for name, shape in items.items():
        export_step(shape, os.path.join(out_dir, f"{name}.step"))
    return list(items.keys())
