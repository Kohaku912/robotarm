"""Report imported servo STEP topology used to define mounting datums."""

import json
import sys

import FreeCAD as App
import Part


def report(path: str) -> dict[str, object]:
    shape = Part.Shape()
    shape.read(path)
    circles: list[dict[str, object]] = []
    for edge in shape.Edges:
        try:
            curve = edge.Curve
        except TypeError:
            continue
        if curve.__class__.__name__ != "Circle":
            continue
        circles.append(
            {
                "radius_mm": round(float(curve.Radius), 6),
                "center_mm": [round(float(v), 6) for v in (curve.Center.x, curve.Center.y, curve.Center.z)],
                "axis": [round(float(v), 6) for v in (curve.Axis.x, curve.Axis.y, curve.Axis.z)],
            }
        )
    box = shape.BoundBox
    return {
        "file": path,
        "solids": len(shape.Solids),
        "volume_mm3": round(float(shape.Volume), 6),
        "bbox_mm": {
            "min": [box.XMin, box.YMin, box.ZMin],
            "max": [box.XMax, box.YMax, box.ZMax],
        },
        "circles_r1_to_r4_mm": [item for item in circles if 1.0 <= item["radius_mm"] <= 4.0],
    }


print(json.dumps(report(sys.argv[1]), indent=2))
