"""2D sketch → extrude (Pad) helpers. Pure Part API for FreeCAD scripting reliability."""

from __future__ import annotations

from typing import Iterable, List, Sequence, Tuple

import FreeCAD as App
import Part

Point2 = Tuple[float, float]


def V(x: float, y: float = 0.0, z: float = 0.0) -> App.Vector:
    return App.Vector(x, y, z)


def wire_from_xy(points: Sequence[Point2], closed: bool = True) -> Part.Wire:
    """Build a wire in the XY plane from 2D points (mm)."""
    if len(points) < 2:
        raise ValueError("need >=2 points")
    vecs = [V(p[0], p[1], 0.0) for p in points]
    if closed and (abs(vecs[0].x - vecs[-1].x) > 1e-9 or abs(vecs[0].y - vecs[-1].y) > 1e-9):
        vecs.append(vecs[0])
    edges = [Part.LineSegment(vecs[i], vecs[i + 1]).toShape() for i in range(len(vecs) - 1)]
    return Part.Wire(edges)


def pad_xy(points: Sequence[Point2], thickness: float, z0: float = 0.0) -> Part.Shape:
    """Extrude a closed XY profile along +Z (Sketch → Pad)."""
    face = Part.Face(wire_from_xy(points, closed=True))
    solid = face.extrude(V(0, 0, thickness))
    if z0:
        solid.translate(V(0, 0, z0))
    return solid


def pad_on_plane(
    points: Sequence[Point2],
    thickness: float,
    plane: str = "xy",
    origin: Sequence[float] = (0, 0, 0),
) -> Part.Shape:
    """
    Extrude 2D profile on xy / xz / yz.
    points are (u,v) in the plane's local 2D coords.
    """
    face = Part.Face(wire_from_xy(points, closed=True))
    if plane == "xy":
        solid = face.extrude(V(0, 0, thickness))
    elif plane == "xz":
        # map (u,v)=(x,z) then extrude +Y
        solid = face.extrude(V(0, 0, thickness))
        solid.rotate(V(0, 0, 0), V(1, 0, 0), 90)
    elif plane == "yz":
        solid = face.extrude(V(0, 0, thickness))
        solid.rotate(V(0, 0, 0), V(0, 1, 0), -90)
    else:
        raise ValueError(plane)
    solid.translate(V(*origin))
    return solid


def cyl(r: float, h: float, origin=(0, 0, 0), axis: str = "z") -> Part.Shape:
    s = Part.makeCylinder(r, h)
    if axis == "x":
        s.rotate(V(0, 0, 0), V(0, 1, 0), 90)
    elif axis == "y":
        s.rotate(V(0, 0, 0), V(1, 0, 0), -90)
    s.translate(V(*origin))
    return s


def fuse(shapes: Iterable[Part.Shape]) -> Part.Shape:
    shapes = [s for s in shapes if s is not None]
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


def aabb_size(shape: Part.Shape) -> Tuple[float, float, float]:
    bb = shape.BoundBox
    return bb.XLength, bb.YLength, bb.ZLength


def assert_print_size(shape: Part.Shape, name: str, limit: float = 180.0):
    sx, sy, sz = aabb_size(shape)
    if max(sx, sy, sz) > limit + 1e-3:
        raise ValueError(f"{name} exceeds print volume: {sx:.1f}x{sy:.1f}x{sz:.1f}")
    return sx, sy, sz


def ibeam_profile(width: float, height: float, flange: float, web: float) -> List[Point2]:
    """Closed I-beam outer profile centered at origin (YZ as XY for extrusion along X later)."""
    w2, h2 = width / 2, height / 2
    web2 = web / 2
    # outer rectangle with inner notches — actually solid I as outer path for pad then pocket,
    # simpler: return outer rect; web/flange built as fused pads.
    return [(-w2, -h2), (w2, -h2), (w2, h2), (-w2, h2)]


def wire_from_yz(points: Sequence[Point2], closed: bool = True) -> Part.Wire:
    """Wire in YZ plane from (y,z) points."""
    vecs = [V(0.0, p[0], p[1]) for p in points]
    if closed and (abs(vecs[0].y - vecs[-1].y) > 1e-9 or abs(vecs[0].z - vecs[-1].z) > 1e-9):
        vecs.append(vecs[0])
    edges = [Part.LineSegment(vecs[i], vecs[i + 1]).toShape() for i in range(len(vecs) - 1)]
    return Part.Wire(edges)


def pad_yz(points: Sequence[Point2], length: float, x0: float = 0.0) -> Part.Shape:
    """Extrude YZ profile along +X (Sketch on YZ → Pad)."""
    face = Part.Face(wire_from_yz(points, closed=True))
    solid = face.extrude(V(length, 0, 0))
    if x0:
        solid.translate(V(x0, 0, 0))
    return solid


def make_ibeam_along_x(length: float, width: float, height: float, flange: float, web: float) -> Part.Shape:
    """I-beam by extruding three 2D rectangles on YZ along X."""
    z0 = -height / 2
    bot = pad_yz(
        [(-width / 2, z0), (width / 2, z0), (width / 2, z0 + flange), (-width / 2, z0 + flange)],
        length,
    )
    top = pad_yz(
        [
            (-width / 2, height / 2 - flange),
            (width / 2, height / 2 - flange),
            (width / 2, height / 2),
            (-width / 2, height / 2),
        ],
        length,
    )
    web_s = pad_yz(
        [
            (-web / 2, z0 + flange),
            (web / 2, z0 + flange),
            (web / 2, height / 2 - flange),
            (-web / 2, height / 2 - flange),
        ],
        length,
    )
    return fuse([bot, top, web_s])


def svg_path_from_points(points: Sequence[Point2], scale: float = 1.0, ox: float = 0, oy: float = 0) -> str:
    cmds = []
    for i, (x, y) in enumerate(points):
        X, Y = ox + x * scale, oy - y * scale
        cmds.append(("M" if i == 0 else "L") + f"{X:.2f} {Y:.2f}")
    cmds.append("Z")
    return " ".join(cmds)


def write_svg(path: str, title: str, polylines: List[Tuple[str, Sequence[Point2]]], width=400, height=300, scale=2.0):
    """Simple dimensioned-ish 2D drawing export."""
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        f"<title>{title}</title>",
        '<rect width="100%" height="100%" fill="#f7f7f4"/>',
        f'<text x="12" y="20" font-family="Segoe UI,sans-serif" font-size="14">{title}</text>',
        '<g stroke="#1a1a1a" stroke-width="1.2" fill="none">',
    ]
    cx, cy = width / 2, height / 2 + 10
    for label, pts in polylines:
        d = svg_path_from_points(pts, scale=scale, ox=cx, oy=cy)
        parts.append(f'<path d="{d}" />')
        parts.append(
            f'<text x="{cx}" y="{height - 16}" font-family="Segoe UI,sans-serif" font-size="11" fill="#333">{label}</text>'
        )
    parts.append("</g></svg>")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))
