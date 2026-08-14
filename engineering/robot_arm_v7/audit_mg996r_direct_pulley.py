"""Validate generated direct-pulley CAD and STL deliverables."""

from pathlib import Path
import json

import FreeCAD as App
import Mesh


ROOT = Path("C:/Users/kohak/programs/robotarm/engineering/robot_arm_v7/direct_spline_pulley")
doc = App.openDocument(str(ROOT / "MG996R_DIRECT_16T_3GT_PROTOTYPE.FCStd"))
pulley = doc.getObject("DIRECT_16T_3GT_PULLEY")
coupon = doc.getObject("SPLINE_CLEARANCE_COUPON")
servo_reference = doc.getObject("MG996R_ASSEMBLY_REFERENCE")
installed_reference = doc.getObject("DIRECT_PULLEY_INSTALLED_REFERENCE")


def mesh_result(filename: str) -> dict:
    mesh = Mesh.Mesh(str(ROOT / filename))
    bb = mesh.BoundBox
    return {
        "file": filename,
        "facets": mesh.CountFacets,
        "solid": bool(mesh.isSolid()),
        "bbox_mm": [round(bb.XLength, 3), round(bb.YLength, 3), round(bb.ZLength, 3)],
    }


checks = [
    {
        "id": "DIRECT-PULLEY-BREP",
        "pass": bool(pulley and pulley.Shape.isValid() and len(pulley.Shape.Solids) == 1),
        "evidence": {"solids": len(pulley.Shape.Solids), "volume_mm3": round(pulley.Shape.Volume, 3)},
    },
    {
        "id": "SPLINE-COUPON-BREP",
        "pass": bool(coupon and coupon.Shape.isValid() and len(coupon.Shape.Solids) == 1),
        "evidence": {"solids": len(coupon.Shape.Solids), "volume_mm3": round(coupon.Shape.Volume, 3)},
    },
]
installed_common_mm3 = installed_reference.Shape.common(servo_reference.Shape).Volume
checks.append({
    "id": "INSTALLED-SERVO-COMMON-VOLUME",
    "pass": installed_common_mm3 <= 0.01,
    "evidence": {"common_volume_mm3": round(installed_common_mm3, 6)},
})
meshes = [
    mesh_result("MG996R_DIRECT_16T_3GT_PULLEY.stl"),
    mesh_result("MG996R_SPLINE_CLEARANCE_COUPON_005_010_015.stl"),
]
checks.append({"id": "STL-CLOSED-SOLIDS", "pass": all(item["solid"] for item in meshes), "evidence": meshes})
checks.append({
    "id": "PHYSICAL-FIT-AND-LOAD",
    "pass": False,
    "evidence": "Pending spline coupon, center-thread, runout, 30 s hold, belt tracking, servo-bearing play/temperature tests",
})

report = {
    "status": "PROTOTYPE_NOT_LOAD_APPROVED",
    "source": "vendor/servo_cad/MG996R_SERVO.step",
    "pulley": {
        "teeth": 16,
        "pitch_mm": 3.0,
        "belt_width_mm": 9.0,
        "socket_radial_clearance_mm": 0.10,
        "mass_estimate_g_at_1_06_g_cm3": round(pulley.Shape.Volume / 1000.0 * 1.06, 3),
    },
    "checks": checks,
}
(ROOT / "MG996R_DIRECT_16T_3GT_AUDIT.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

print(json.dumps(report, ensure_ascii=False, indent=2))
if not all(check["pass"] for check in checks if check["id"] != "PHYSICAL-FIT-AND-LOAD"):
    raise SystemExit(1)
