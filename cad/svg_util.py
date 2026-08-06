"""SVG helpers without FreeCAD dependency."""

from __future__ import annotations

from typing import List, Sequence, Tuple

Point2 = Tuple[float, float]


def svg_path_from_points(points: Sequence[Point2], scale: float = 1.0, ox: float = 0, oy: float = 0) -> str:
    cmds = []
    for i, (x, y) in enumerate(points):
        X, Y = ox + x * scale, oy - y * scale
        cmds.append(("M" if i == 0 else "L") + f"{X:.2f} {Y:.2f}")
    cmds.append("Z")
    return " ".join(cmds)


def write_svg(path: str, title: str, polylines: List[Tuple[str, Sequence[Point2]]], width=400, height=300, scale=2.0):
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
            f'<text x="16" y="{height - 16}" font-family="Segoe UI,sans-serif" font-size="11" fill="#333">{label}</text>'
        )
    parts.append("</g></svg>")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))
