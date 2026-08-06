"""
Generate FreeCAD docs, STLs, vendor STEP, 2D SVG, URDF meshes.

exec(open(r'C:/Users/kohak/programs/robotarm/generate_arm.py', encoding='utf-8').read())
"""

from __future__ import annotations

import json
import os
import sys
import traceback

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import FreeCAD as App
import Mesh
import Part

import params as P
from cad.export_svg import main as export_svg
from cad.sketch_pad import assert_print_size, translate
from parts import base_j1, shoulder_j2, upper_arm, elbow_j3, forearm, wrist, gripper, camera_mount, hardware
from vendor import models as vendor_models

EXPORT_STL = os.path.join(ROOT, "export", "stl")
EXPORT_FCSTD = os.path.join(ROOT, "export", "fcstd")
EXPORT_VENDOR = os.path.join(ROOT, "export", "vendor")
URDF_MESH = os.path.join(ROOT, "urdf", "meshes")
REPORT_PATH = os.path.join(ROOT, "export", "generation_report.json")


def ensure_dirs():
    for d in (EXPORT_STL, EXPORT_FCSTD, EXPORT_VENDOR, URDF_MESH, os.path.join(ROOT, "docs", "2d")):
        os.makedirs(d, exist_ok=True)


def collect_parts():
    parts = {}
    for mod in (base_j1, shoulder_j2, upper_arm, elbow_j3, forearm, wrist, gripper, camera_mount):
        parts.update(mod.make_all())
    refs = {
        "ref_MG996R": hardware.mg996r_body(),
        "ref_MG90S": hardware.mg90s_body(),
        "ref_F695ZZ": hardware.bearing_f695zz(),
        "ref_F685ZZ": hardware.bearing_f685zz(),
    }
    return parts, refs


def export_stl(name: str, shape: Part.Shape, folder: str) -> str:
    path = os.path.join(folder, f"{name}.stl")
    try:
        import MeshPart

        mesh = MeshPart.meshFromShape(Shape=shape, LinearDeflection=0.2, AngularDeflection=0.2)
        mesh.write(path)
    except Exception:
        tmp = App.newDocument("tmp_stl")
        obj = tmp.addObject("Part::Feature", name)
        obj.Shape = shape
        tmp.recompute()
        Mesh.export([obj], path)
        App.closeDocument(tmp.Name)
    return path


def add_shape(doc, name, shape):
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = shape
    return obj


def build_assembly(doc, printed):
    add_shape(doc, "ASM_base_plate", printed["01_base_plate"])
    add_shape(doc, "ASM_base_column", printed["02_base_column"])
    tur = printed["03_turret"].copy()
    tur.translate(App.Vector(0, 0, P.TURNTABLE_Z - 5))
    add_shape(doc, "ASM_turret", tur)

    z = P.SHOULDER_PIVOT_Z
    sh = printed["04_shoulder_horn_clamp"].copy()
    sh.translate(App.Vector(8, -(P.YOKE_INNER / 2 + 8), z))
    add_shape(doc, "ASM_shoulder_horn", sh)
    idl = printed["05_shoulder_idler_cap"].copy()
    idl.translate(App.Vector(8, P.YOKE_INNER / 2 + 8, z))
    add_shape(doc, "ASM_shoulder_idler", idl)

    ua = printed["06_upper_arm_a"].copy()
    ua.translate(App.Vector(18, 0, z))
    add_shape(doc, "ASM_upper_a", ua)
    ub = printed["07_upper_arm_b"].copy()
    ub.translate(App.Vector(18 + P.UPPER_SEG_A, 0, z))
    add_shape(doc, "ASM_upper_b", ub)

    x = 18 + P.L_UPPER + 10
    eh = printed["08_elbow_horn_clamp"].copy()
    eh.translate(App.Vector(x, 0, z))
    add_shape(doc, "ASM_elbow_horn", eh)

    fa = printed["10_forearm_a"].copy()
    fa.translate(App.Vector(x + 12, 0, z))
    add_shape(doc, "ASM_fore_a", fa)
    fb = printed["11_forearm_b"].copy()
    fb.translate(App.Vector(x + 12 + P.FORE_SEG_A, 0, z))
    add_shape(doc, "ASM_fore_b", fb)

    xw = x + 12 + P.L_FOREARM + 8
    for name, key, dx, dz in (
        ("ASM_wrist_pitch", "12_wrist_pitch_yoke", 0, 0),
        ("ASM_wrist_roll", "13_wrist_roll_carrier", 30, 0),
        ("ASM_wrist_yaw", "14_wrist_yaw_flange", 62, 0),
        ("ASM_gripper", "15_gripper_body", 70, 0),
        ("ASM_cam_tilt", "20_camera_tilt_mount", 70, 22),
        ("ASM_cam_bracket", "19_camera_bracket", 70, 42),
    ):
        s = printed[key].copy()
        s.translate(App.Vector(xw + dx, 0, z + dz))
        add_shape(doc, name, s)

    # Home envelope from placed assembly objects
    mins = [1e9, 1e9, 1e9]
    maxs = [-1e9, -1e9, -1e9]
    for o in doc.Objects:
        if not o.Name.startswith("ASM_"):
            continue
        try:
            bb = o.Shape.BoundBox
            mins[0] = min(mins[0], bb.XMin)
            mins[1] = min(mins[1], bb.YMin)
            mins[2] = min(mins[2], bb.ZMin)
            maxs[0] = max(maxs[0], bb.XMax)
            maxs[1] = max(maxs[1], bb.YMax)
            maxs[2] = max(maxs[2], bb.ZMax)
        except Exception:
            pass
    env = (maxs[0] - mins[0], maxs[1] - mins[1], maxs[2] - mins[2])
    return {"reach_marker": xw + 70, "envelope_mm": [round(v, 1) for v in env]}


def write_urdf(mesh_map, path, volumes=None):
    """Serial-chain URDF with params-aligned origins; mesh visual + box collision."""
    volumes = volumes or {}
    dens = P.PLA_DENSITY  # g/mm^3
    L1 = P.TURNTABLE_Z / 1000.0
    L2 = P.SHOULDER_OFFSET / 1000.0
    Lu = P.L_UPPER / 1000.0
    Lf = P.L_FOREARM / 1000.0
    Lw = (P.L_WRIST / 3) / 1000.0

    def mesh_tag(key):
        rel = mesh_map.get(key, "meshes/01_base_plate.stl")
        return f'<mesh filename="{rel}" scale="0.001 0.001 0.001"/>'

    def mass_of(key, default_g=50.0):
        v = volumes.get(key)
        if v:
            return max(0.01, (v * dens) / 1000.0)
        return default_g / 1000.0

    def inertial(mass, sx=0.03, sy=0.03, sz=0.03):
        ixx = mass * (sy * sy + sz * sz) / 12.0
        iyy = mass * (sx * sx + sz * sz) / 12.0
        izz = mass * (sx * sx + sy * sy) / 12.0
        return f"""<inertial>
      <mass value="{mass:.5f}"/>
      <inertia ixx="{ixx:.8f}" ixy="0" ixz="0" iyy="{iyy:.8f}" iyz="0" izz="{izz:.8f}"/>
    </inertial>"""

    links = [
        ("base_link", "01_base_plate", (0.11, 0.11, 0.008), 80),
        ("turret_link", "03_turret", (0.056, 0.05, 0.055), 55),
        ("upper_link", "06_upper_arm_a", (Lu, 0.036, 0.028), 40),
        ("fore_link", "10_forearm_a", (Lf, 0.032, 0.026), 35),
        ("wrist_pitch_link", "12_wrist_pitch_yoke", (0.04, 0.024, 0.03), 22),
        ("wrist_roll_link", "13_wrist_roll_carrier", (0.04, 0.028, 0.028), 22),
        ("wrist_yaw_link", "14_wrist_yaw_flange", (0.024, 0.024, 0.008), 12),
        ("gripper_link", "15_gripper_body", (0.042, 0.032, 0.024), 30),
        ("camera_link", "19_camera_bracket", (0.06, 0.02, 0.01), 12),
    ]

    jl = P.JOINT_LIMITS
    joints = [
        ("j1", "base_link", "turret_link", (0, 0, L1), (0, 0, 1), jl["j1"]),
        ("j2", "turret_link", "upper_link", (L2, 0, 0.01), (0, 1, 0), jl["j2"]),
        ("j3", "upper_link", "fore_link", (Lu, 0, 0), (0, 1, 0), jl["j3"]),
        ("j4", "fore_link", "wrist_pitch_link", (Lf, 0, 0), (0, 1, 0), jl["j4"]),
        ("j5", "wrist_pitch_link", "wrist_roll_link", (Lw, 0, 0), (1, 0, 0), jl["j5"]),
        ("j6", "wrist_roll_link", "wrist_yaw_link", (Lw, 0, 0), (0, 0, 1), jl["j6"]),
        ("gripper", "wrist_yaw_link", "gripper_link", (0.02, 0, 0), (0, 0, 1), jl["gripper"]),
        ("camera_tilt", "gripper_link", "camera_link", (0, 0, 0.028), (0, 1, 0), jl["camera_tilt"]),
    ]

    lines = ['<?xml version="1.0"?>', '<robot name="robotarm">']
    for name, mesh_key, box, def_g in links:
        m = mass_of(mesh_key, def_g)
        lines.append(f'  <link name="{name}">')
        lines.append(f"    {inertial(m, *box)}")
        lines.append("    <visual>")
        lines.append("      <geometry>")
        lines.append(f"        {mesh_tag(mesh_key)}")
        lines.append("      </geometry>")
        lines.append('      <material name="pla"><color rgba="0.75 0.78 0.82 1"/></material>')
        lines.append("    </visual>")
        # Simplified box collision for stable contact tests
        lines.append("    <collision>")
        if name in ("upper_link", "fore_link", "wrist_pitch_link", "wrist_roll_link"):
            lines.append(f'      <origin xyz="{box[0] / 2:.4f} 0 0" rpy="0 0 0"/>')
        else:
            lines.append('      <origin xyz="0 0 0" rpy="0 0 0"/>')
        lines.append("      <geometry>")
        lines.append(f'        <box size="{box[0]:.4f} {box[1]:.4f} {box[2]:.4f}"/>')
        lines.append("      </geometry>")
        lines.append("    </collision>")
        lines.append("  </link>")
    for jname, parent, child, xyz, axis, lim in joints:
        lines.append(f'  <joint name="{jname}" type="revolute">')
        lines.append(f'    <parent link="{parent}"/>')
        lines.append(f'    <child link="{child}"/>')
        lines.append(f'    <origin xyz="{xyz[0]:.5f} {xyz[1]:.5f} {xyz[2]:.5f}" rpy="0 0 0"/>')
        lines.append(f'    <axis xyz="{axis[0]} {axis[1]} {axis[2]}"/>')
        lines.append(
            f'    <limit lower="{lim[0]}" upper="{lim[1]}" effort="{20 if jname in ("j1","j2") else 5}" velocity="2"/>'
        )
        lines.append('    <dynamics damping="0.08" friction="0.02"/>')
        lines.append("  </joint>")

    lines.append("</robot>")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main():
    ensure_dirs()
    report = {"parts": {}, "errors": [], "ok": False, "reach_mm_approx": None, "svg": [], "vendor": []}

    for name in list(App.listDocuments().keys()):
        if name.startswith("RobotArm") or name == "tmp_stl":
            App.closeDocument(name)

    # 2D drawings
    try:
        report["svg"] = export_svg(os.path.join(ROOT, "docs", "2d"))
    except Exception as e:
        report["errors"].append({"stage": "svg", "error": str(e), "trace": traceback.format_exc()})

    # vendor STEP
    try:
        report["vendor"] = vendor_models.export_all(EXPORT_VENDOR)
    except Exception as e:
        report["errors"].append({"stage": "vendor", "error": str(e), "trace": traceback.format_exc()})

    try:
        printed, refs = collect_parts()
    except Exception as e:
        report["errors"].append({"stage": "collect", "error": str(e), "trace": traceback.format_exc()})
        with open(REPORT_PATH, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        raise

    mesh_map = {}
    volumes = {}
    for name, shape in printed.items():
        try:
            sx, sy, sz = assert_print_size(shape, name, P.PRINT_MAX)
            stl = export_stl(name, shape, EXPORT_STL)
            export_stl(name, shape, URDF_MESH)
            mesh_map[name] = f"meshes/{name}.stl"
            volumes[name] = shape.Volume
            report["parts"][name] = {
                "bbox": [round(sx, 2), round(sy, 2), round(sz, 2)],
                "volume_mm3": round(shape.Volume, 1),
                "stl": stl,
            }
        except Exception as e:
            report["errors"].append({"part": name, "error": str(e), "trace": traceback.format_exc()})

    # fastener expectations for validation
    from parts.fastener_spec import FASTENER_REQUIREMENTS

    with open(os.path.join(ROOT, "export", "fastener_requirements.json"), "w", encoding="utf-8") as f:
        json.dump(FASTENER_REQUIREMENTS, f, indent=2)
    parts_doc = App.newDocument("RobotArm_Parts")
    x_off = 0.0
    for name, shape in printed.items():
        s = shape.copy()
        bb = s.BoundBox
        s.translate(App.Vector(x_off - bb.XMin, -bb.YMin, -bb.ZMin))
        add_shape(parts_doc, name, s)
        x_off += bb.XLength + 15
    parts_doc.recompute()
    parts_path = os.path.join(EXPORT_FCSTD, "RobotArm_Parts.FCStd")
    parts_doc.saveAs(parts_path)

    asm = App.newDocument("RobotArm")
    try:
        asm_info = build_assembly(asm, printed)
        report["reach_mm_approx"] = asm_info["reach_marker"]
        report["envelope_mm"] = asm_info["envelope_mm"]
        ex, ey, ez = asm_info["envelope_mm"]
        mx, my, mz = P.ENVELOPE_MAX
        report["envelope_ok"] = ex <= mx + 5 and ey <= my + 5 and ez <= mz + 5
        if not report["envelope_ok"]:
            report["errors"].append(
                {
                    "stage": "envelope",
                    "error": f"home envelope {ex}x{ey}x{ez} exceeds target {mx}x{my}x{mz}",
                }
            )
        add_shape(asm, "REF_MG996R", translate(refs["ref_MG996R"], 0, 50, 15))
        add_shape(asm, "REF_MG90S", translate(refs["ref_MG90S"], 40, 50, 15))
    except Exception as e:
        report["errors"].append({"stage": "assembly", "error": str(e), "trace": traceback.format_exc()})
    asm.recompute()
    asm_path = os.path.join(EXPORT_FCSTD, "RobotArm.FCStd")
    asm.saveAs(asm_path)

    urdf_path = os.path.join(ROOT, "urdf", "robot_arm.urdf")
    try:
        write_urdf(mesh_map, urdf_path, volumes)
        report["urdf"] = urdf_path
    except Exception as e:
        report["errors"].append({"stage": "urdf", "error": str(e), "trace": traceback.format_exc()})

    report["fcstd_parts"] = parts_path
    report["fcstd_assembly"] = asm_path
    report["ok"] = len(report["errors"]) == 0
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    return report


if __name__ == "__main__":
    main()
