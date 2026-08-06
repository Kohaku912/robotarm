"""FreeCAD Part geometry helpers."""

from __future__ import annotations

import math
from typing import Iterable, Sequence, Tuple

import FreeCAD as App
import Part

Vec = App.Vector


def V(x: float, y: float = 0.0, z: float = 0.0) -> Vec:
    return App.Vector(x, y, z)


def box(lx: float, ly: float, lz: float, origin: Sequence[float] = (0, 0, 0)) -> Part.Shape:
    s = Part.makeBox(lx, ly, lz)
    s.translate(V(*origin))
    return s


def cyl(
    r: float,
    h: float,
    origin: Sequence[float] = (0, 0, 0),
    axis: str = "z",
) -> Part.Shape:
    s = Part.makeCylinder(r, h)
    if axis == "x":
        s.rotate(V(0, 0, 0), V(0, 1, 0), 90)
    elif axis == "y":
        s.rotate(V(0, 0, 0), V(1, 0, 0), -90)
    s.translate(V(*origin))
    return s


def fuse(shapes: Iterable[Part.Shape]) -> Part.Shape:
    shapes = [s for s in shapes if s is not None]
    if not shapes:
        raise ValueError("fuse: empty")
    out = shapes[0]
    for s in shapes[1:]:
        out = out.fuse(s)
    return out.removeSplitter()


def cut(base: Part.Shape, tools: Iterable[Part.Shape]) -> Part.Shape:
    out = base
    for t in tools:
        if t is not None:
            out = out.cut(t)
    return out.removeSplitter()


def translate(shape: Part.Shape, dx: float, dy: float = 0.0, dz: float = 0.0) -> Part.Shape:
    s = shape.copy()
    s.translate(V(dx, dy, dz))
    return s


def rotate(shape: Part.Shape, axis: Sequence[float], angle_deg: float, center=(0, 0, 0)) -> Part.Shape:
    s = shape.copy()
    s.rotate(V(*center), V(*axis), angle_deg)
    return s


def mirror_xz(shape: Part.Shape) -> Part.Shape:
    return shape.mirror(V(0, 0, 0), V(0, 1, 0))


def aabb_size(shape: Part.Shape) -> Tuple[float, float, float]:
    bb = shape.BoundBox
    return bb.XLength, bb.YLength, bb.ZLength


def assert_print_size(shape: Part.Shape, name: str, limit: float = 180.0) -> Tuple[float, float, float]:
    sx, sy, sz = aabb_size(shape)
    mx = max(sx, sy, sz)
    if mx > limit + 1e-3:
        raise ValueError(f"{name} exceeds print volume: {sx:.1f}x{sy:.1f}x{sz:.1f} > {limit}")
    return sx, sy, sz


def countersink_hole(
    clear_d: float,
    head_d: float,
    head_h: float,
    length: float,
    origin: Sequence[float],
    axis: str = "z",
) -> Part.Shape:
    """Clearance through + cylindrical head recess."""
    r = clear_d / 2
    hr = head_d / 2
    shank = cyl(r, length, origin, axis)
    if axis == "z":
        head = cyl(hr, head_h, origin, axis)
    elif axis == "x":
        head = cyl(hr, head_h, origin, axis)
    else:
        head = cyl(hr, head_h, origin, axis)
    return fuse([shank, head])


def insert_hole(od: float, depth: float, origin: Sequence[float], axis: str = "z") -> Part.Shape:
    return cyl(od / 2, depth, origin, axis)


def cable_channel(d: float, length: float, origin: Sequence[float], axis: str = "x") -> Part.Shape:
    return cyl(d / 2, length, origin, axis)


def ibeam(length: float, width: float, height: float, flange: float, web: float) -> Part.Shape:
    """I-beam along +X, centered on YZ at origin start."""
    # bottom flange
    bot = box(length, width, flange, (0, -width / 2, -height / 2))
    top = box(length, width, flange, (0, -width / 2, height / 2 - flange))
    web_s = box(length, web, height - 2 * flange, (0, -web / 2, -height / 2 + flange))
    return fuse([bot, top, web_s])


def rounded_plate(od: float, thick: float) -> Part.Shape:
    return cyl(od / 2, thick)


def servo_pocket_mg996r(p: dict, extra: float = 0.4) -> Part.Shape:
    """Body cavity centered at origin, body along X, height Z up, spline toward +Z top."""
    bl = p["body_l"] + 2 * extra
    bw = p["body_w"] + 2 * extra
    bh = p["body_h"] + extra
    body = box(bl, bw, bh, (-bl / 2, -bw / 2, -bh / 2))
    # cable exit -Y side bottom
    cable = box(p["cable_clear_w"], 8, p["cable_clear_h"], (-p["cable_clear_w"] / 2, -bw / 2 - 6, -bh / 2))
    return fuse([body, cable])


def servo_pocket_mg90s(p: dict, extra: float = 0.4) -> Part.Shape:
    bl = p["body_l"] + 2 * extra
    bw = p["body_w"] + 2 * extra
    bh = p["body_h"] + extra
    body = box(bl, bw, bh, (-bl / 2, -bw / 2, -bh / 2))
    cable = box(p["cable_clear_w"], 6, p["cable_clear_h"], (-p["cable_clear_w"] / 2, -bw / 2 - 4, -bh / 2))
    return fuse([body, cable])


def servo_tab_holes_mg996r(p: dict, z: float, axis_along_x: bool = True) -> Part.Shape:
    """Four mounting holes through tabs (approximate)."""
    along = p["tab_hole_along"] / 2
    across = 5.0
    d = p["tab_hole_d"]
    holes = []
    for x in (-along, along):
        for y in (-across, across):
            holes.append(cyl(d / 2, 20, (x, y, z - 10)))
    return fuse(holes)


def servo_tab_holes_mg90s(p: dict, z: float) -> Part.Shape:
    along = p["tab_hole_along"] / 2
    d = p["tab_hole_d"]
    holes = []
    for x in (-along, along):
        holes.append(cyl(d / 2, 16, (x, 0, z - 8)))
    return fuse(holes)


def bearing_pocket(bearing: dict, flange_side: str = "+z") -> Part.Shape:
    """
    Bearing pocket: OD seat + flange recess.
    Bearing sits with axis along Z, flange on flange_side.
    """
    od = bearing["seat_od"]
    w = bearing["width"] + 0.2
    fod = bearing["flange_seat"]
    ft = bearing["flange_t"] + 0.15
    seat = cyl(od / 2, w, (0, 0, -w / 2))
    if flange_side == "+z":
        flange = cyl(fod / 2, ft, (0, 0, w / 2 - ft))
    else:
        flange = cyl(fod / 2, ft, (0, 0, -w / 2))
    return fuse([seat, flange])


def horn_boss(outer_d: float, inner_d: float, height: float) -> Part.Shape:
    outer = cyl(outer_d / 2, height)
    inner = cyl(inner_d / 2, height + 1, (0, 0, -0.5))
    return cut(outer, [inner])


def split_joint_features(
    face_x: float,
    width: float,
    height: float,
    insert: dict,
    dowel_d: float,
    spacing: float,
    male: bool,
) -> Tuple[Part.Shape, Part.Shape]:
    """
    Returns (add_solid, cut_solid) for a split plane at x=face_x.
    Male: protruding dowels + clearance holes for bolts.
    Female: dowel holes + insert holes.
    """
    adds = []
    cuts = []
    ys = (-spacing / 2, spacing / 2)
    zs = (-spacing / 2, spacing / 2)
    # four corners around center
    positions = [(0, y, z) for y in ys for z in zs]
    # simplify to 4 positions in YZ
    positions = [
        (face_x, -spacing / 2, -spacing / 2),
        (face_x, spacing / 2, -spacing / 2),
        (face_x, -spacing / 2, spacing / 2),
        (face_x, spacing / 2, spacing / 2),
    ]
    for px, py, pz in positions:
        if male:
            # dowel protrusion along +X from face
            adds.append(cyl(dowel_d / 2 - 0.1, 5.0, (px, py, pz), "x"))
            # bolt clearance through
            cuts.append(cyl(insert["clear_d"] / 2, 30, (px - 15, py, pz), "x"))
            cuts.append(cyl(insert["head_d"] / 2, insert["head_h"] + 0.3, (px - 3, py, pz), "x"))
        else:
            cuts.append(cyl(dowel_d / 2 + 0.15, 5.5, (px - 0.5, py, pz), "x"))
            cuts.append(insert_hole(insert["insert_hole"], insert["insert_depth"], (px - 0.2, py, pz), "x"))
    add_s = fuse(adds) if adds else None
    cut_s = fuse(cuts) if cuts else None
    return add_s, cut_s
